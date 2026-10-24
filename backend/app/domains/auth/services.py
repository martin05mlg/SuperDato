import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.audit import audit
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_signature,
    hash_password,
    verify_password,
)
from app.domains.auth.models import User, RegistrationToken
from app.domains.auth.schemas import (
    InitialAdminSetupRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from app.domains.households.models import Household, HouseholdMembership

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


class AuthService:
    @staticmethod
    async def get_setup_status(db: AsyncSession) -> dict:
        result = await db.execute(select(func.count(User.id)))
        count = result.scalar() or 0
        return {
            "needs_setup": count == 0,
            "app_name": settings.APP_NAME,
        }

    @staticmethod
    async def setup_initial_admin(db: AsyncSession, data: InitialAdminSetupRequest) -> TokenResponse:
        result = await db.execute(select(func.count(User.id)))
        count = result.scalar() or 0
        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El sistema ya ha sido inicializado. No es posible crear el administrador inicial.",
            )

        clean_email = data.email.lower().strip()
        user = User(
            id=uuid.uuid4(),
            email=clean_email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name.strip(),
            is_active=True,
            is_verified=True,
            is_superuser=True,
            must_change_password=False,
        )
        db.add(user)
        await db.flush()

        household = Household(
            id=uuid.uuid4(),
            name=f"Hogar de {user.full_name}",
            currency="EUR",
            created_by_user_id=user.id,
        )
        db.add(household)
        await db.flush()

        membership = HouseholdMembership(
            id=uuid.uuid4(),
            household_id=household.id,
            user_id=user.id,
            role="OWNER",
        )
        db.add(membership)

        if settings.AUTO_SEED_SAMPLES:
            try:
                from app.domains.receipts.services import ReceiptService
                await ReceiptService.sync_sample_receipts_to_db(db)
            except Exception as e:
                import logging
                logging.getLogger("superdato.setup").warning("Error al sembrar tickets sintéticos en setup: %s", e)

        await db.commit()
        await db.refresh(user)

        audit("first_run_setup_completed", target=clean_email)

        pwd_sig = get_password_signature(user.hashed_password)
        access_token = create_access_token(subject=str(user.id), claims={"pwd_sig": pwd_sig})
        refresh_token = create_refresh_token(subject=str(user.id), claims={"pwd_sig": pwd_sig})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

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

        # User is superadmin if their email matches configured SUPERADMIN_EMAIL
        is_super = data.email.lower().strip() == settings.SUPERADMIN_EMAIL.lower().strip()

        # Create user
        user = User(
            email=data.email.lower().strip(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name.strip(),
            is_active=True,
            is_verified=True,
            is_superuser=is_super,
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
            if data.password == data.current_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La nueva contraseña debe ser distinta de la actual.",
                )
            user.hashed_password = hash_password(data.password)
            user.must_change_password = False
            audit("password_changed", actor=user, target=user.email)

        await db.commit()
        await db.refresh(user)
        return UserResponse.model_validate(user)

    @staticmethod
    async def export_account_data(db: AsyncSession, user: User) -> dict:
        """Exporta todos los datos personales del usuario (derecho de acceso/portabilidad, RGPD)."""
        from sqlalchemy.orm import selectinload
        from app.domains.receipts.models import Receipt

        memberships = (
            await db.execute(select(HouseholdMembership).where(HouseholdMembership.user_id == user.id))
        ).scalars().all()
        household_ids = [m.household_id for m in memberships]
        households = []
        receipts_out = []
        if household_ids:
            hh_rows = (await db.execute(select(Household).where(Household.id.in_(household_ids)))).scalars().all()
            role_by_hh = {m.household_id: m.role for m in memberships}
            households = [
                {"id": str(h.id), "name": h.name, "currency": h.currency, "role": role_by_hh.get(h.id)}
                for h in hh_rows
            ]
            receipts = (
                await db.execute(
                    select(Receipt)
                    .options(selectinload(Receipt.lines), selectinload(Receipt.tax_lines))
                    .where(Receipt.household_id.in_(household_ids))
                    .order_by(Receipt.purchase_datetime)
                )
            ).scalars().all()
            for r in receipts:
                receipts_out.append({
                    "id": str(r.id),
                    "household_id": str(r.household_id),
                    "invoice_number": r.invoice_number,
                    "purchase_datetime": r.purchase_datetime.isoformat() if r.purchase_datetime else None,
                    "store_address": r.store_address,
                    "store_city": r.store_city,
                    "total_amount": float(r.total_amount),
                    "payment_method": r.payment_method,
                    "lines": [
                        {
                            "description": l.raw_description,
                            "quantity": float(l.quantity),
                            "unit_price": float(l.unit_price),
                            "line_total": float(l.line_total),
                        }
                        for l in r.lines
                    ],
                    "tax_lines": [
                        {
                            "rate_percent": float(t.tax_rate_percent),
                            "base": float(t.taxable_base),
                            "tax": float(t.tax_amount),
                            "total": float(t.total_with_tax),
                        }
                        for t in r.tax_lines
                    ],
                })
        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "households": households,
            "receipts": receipts_out,
        }

    @staticmethod
    async def delete_account(db: AsyncSession, user: User, password: str) -> dict:
        """Elimina la cuenta propia (derecho de supresión, RGPD) y los hogares de los que es único miembro."""
        from app.domains.catalog.models import PriceObservation
        from app.domains.receipts.models import Receipt

        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña incorrecta. No se ha eliminado la cuenta.",
            )

        if user.is_superuser:
            other_admins = (
                await db.execute(
                    select(func.count(User.id)).where(User.is_superuser == True, User.id != user.id, User.is_active == True)  # noqa: E712
                )
            ).scalar_one()
            if not other_admins:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Eres el único superadministrador. Promociona a otro usuario antes de eliminar tu cuenta.",
                )

        memberships = (
            await db.execute(select(HouseholdMembership).where(HouseholdMembership.user_id == user.id))
        ).scalars().all()
        for m in memberships:
            member_count = (
                await db.execute(
                    select(func.count(HouseholdMembership.id)).where(HouseholdMembership.household_id == m.household_id)
                )
            ).scalar_one()
            if member_count <= 1:
                # Hogar de un único miembro: se elimina con sus tickets y observaciones de precio
                await db.execute(delete(PriceObservation).where(PriceObservation.household_id == m.household_id))
                receipts = (
                    await db.execute(select(Receipt).where(Receipt.household_id == m.household_id))
                ).scalars().all()
                for r in receipts:
                    await db.delete(r)
                household = (
                    await db.execute(select(Household).where(Household.id == m.household_id))
                ).scalar_one_or_none()
                if household:
                    await db.delete(household)
            elif m.role == "OWNER":
                owners = (
                    await db.execute(
                        select(func.count(HouseholdMembership.id)).where(
                            HouseholdMembership.household_id == m.household_id, HouseholdMembership.role == "OWNER"
                        )
                    )
                ).scalar_one()
                if owners <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Eres el único propietario de un hogar compartido. Transfiere la propiedad antes de eliminar tu cuenta.",
                    )

        audit("account_deleted", actor=user, target=user.email)
        await db.delete(user)
        await db.commit()
        return {"status": "success", "message": "Cuenta y datos personales eliminados."}

