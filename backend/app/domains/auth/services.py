import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_signature,
    hash_password,
    verify_password,
)
from app.domains.auth.models import User, RegistrationToken
from app.domains.auth.schemas import TokenResponse, UserLogin, UserRegister, UserResponse, UserUpdate
from app.domains.households.models import Household, HouseholdMembership

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, data: UserRegister) -> TokenResponse:
        # Check if email is already taken
        query = select(User).where(User.email == data.email.lower().strip())
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una cuenta registrada con este correo electrónico.",
            )

        # Validate registration token issued by superadmin
        token_clean = data.registration_token.strip()
        t_stmt = select(RegistrationToken).where(RegistrationToken.token == token_clean)
        t_res = await db.execute(t_stmt)
        token_obj = t_res.scalar_one_or_none()

        if not token_obj or not token_obj.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token de registro no válido o inactivo. Contacta con el administrador del sistema.",
            )

        if token_obj.expires_at:
            now_utc = datetime.now(timezone.utc)
            exp = token_obj.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < now_utc:
                token_obj.is_active = False
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Este token de registro ha caducado.",
                )

        if token_obj.times_used >= token_obj.max_uses:
            token_obj.is_active = False
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Este token de registro ya ha alcanzado el límite de usos permitidos.",
            )

        # Consume token use
        token_obj.times_used += 1
        if token_obj.times_used >= token_obj.max_uses:
            token_obj.is_active = False

        # Create user
        user = User(
            email=data.email.lower().strip(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name.strip(),
            is_active=True,
            is_verified=True,
            is_superuser=False,
        )
        db.add(user)
        await db.flush()

        # Create initial default household for the user
        household = Household(
            name=f"Hogar de {user.full_name}",
            currency="EUR",
            created_by_user_id=user.id,
        )
        db.add(household)
        await db.flush()

        # Assign user as OWNER of this household
        membership = HouseholdMembership(
            household_id=household.id,
            user_id=user.id,
            role="OWNER",
        )
        db.add(membership)
        await db.commit()
        await db.refresh(user)

        # Generate tokens with password signature claim
        pwd_sig = get_password_signature(user.hashed_password)
        access_token = create_access_token(subject=str(user.id), claims={"pwd_sig": pwd_sig})
        refresh_token = create_refresh_token(subject=str(user.id), claims={"pwd_sig": pwd_sig})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    async def login(db: AsyncSession, data: UserLogin) -> TokenResponse:
        query = select(User).where(User.email == data.email.lower().strip())
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        # Check temporary account lockout due to brute-force attempts
        now_utc = datetime.now(timezone.utc)
        if user and user.locked_until:
            lock_exp = user.locked_until
            if lock_exp.tzinfo is None:
                lock_exp = lock_exp.replace(tzinfo=timezone.utc)
            if lock_exp > now_utc:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Cuenta bloqueada temporalmente por demasiados intentos fallidos. Inténtalo de nuevo más tarde.",
                )
            else:
                user.locked_until = None
                user.failed_login_attempts = 0

        if not user or not verify_password(data.password, user.hashed_password):
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                    user.locked_until = now_utc + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas. Verifica tu email y contraseña.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cuenta desactivada o bloqueada.",
            )

        # Reset failed login attempts upon successful login
        if user.failed_login_attempts > 0 or user.locked_until is not None:
            user.failed_login_attempts = 0
            user.locked_until = None
            await db.commit()

        pwd_sig = get_password_signature(user.hashed_password)
        access_token = create_access_token(subject=str(user.id), claims={"pwd_sig": pwd_sig})
        refresh_token = create_refresh_token(subject=str(user.id), claims={"pwd_sig": pwd_sig})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    async def refresh_token(db: AsyncSession, refresh_token_str: str) -> TokenResponse:
        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido o expirado.",
            )

        user_id_str = payload.get("sub")
        try:
            user_uuid = uuid.UUID(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ID de usuario inválido en token.",
            )

        query = select(User).where(User.id == user_uuid)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no válido para renovación.",
            )

        # Verify password signature to invalidate refresh tokens issued prior to a password change
        token_pwd_sig = payload.get("pwd_sig")
        current_pwd_sig = get_password_signature(user.hashed_password)
        if token_pwd_sig and token_pwd_sig != current_pwd_sig:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token invalidado tras cambio de contraseña. Inicia sesión nuevamente.",
            )

        new_access_token = create_access_token(subject=str(user.id), claims={"pwd_sig": current_pwd_sig})
        new_refresh_token = create_refresh_token(subject=str(user.id), claims={"pwd_sig": current_pwd_sig})

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    async def update_profile(db: AsyncSession, user: User, data: UserUpdate) -> UserResponse:
        if data.full_name is not None:
            user.full_name = data.full_name.strip()
        if data.password is not None:
            if not data.current_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debes proporcionar tu contraseña actual para establecer una nueva contraseña.",
                )
            if not verify_password(data.current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="La contraseña actual proporcionada es incorrecta.",
                )
            user.hashed_password = hash_password(data.password)

        await db.commit()
        await db.refresh(user)
        return UserResponse.model_validate(user)

