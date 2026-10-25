import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.domains.auth.models import RegistrationToken, User
from app.domains.catalog.models import Product
from app.domains.households.models import Household, HouseholdMembership
from app.domains.receipts.models import Receipt


class AdminService:
    @staticmethod
    async def get_system_stats(db: AsyncSession) -> Dict:
        """Calculates global system metrics for superadmin dashboard."""
        users_count = (await db.execute(select(func.count(User.id)))).scalar_one() or 0
        active_users_count = (
            await db.execute(select(func.count(User.id)).where(User.is_active == True))
        ).scalar_one() or 0
        households_count = (await db.execute(select(func.count(Household.id)))).scalar_one() or 0
        receipts_count = (await db.execute(select(func.count(Receipt.id)))).scalar_one() or 0
        products_count = (await db.execute(select(func.count(Product.id)))).scalar_one() or 0
        total_spend = float((await db.execute(select(func.coalesce(func.sum(Receipt.total_amount), 0.0)))).scalar_one() or 0.0)
        tokens_count = (await db.execute(select(func.count(RegistrationToken.id)).where(RegistrationToken.is_active == True))).scalar_one() or 0

        pending_receipts_count = (
            await db.execute(
                select(func.count(Receipt.id)).where(
                    (Receipt.assignment_status == "PENDING_ASSIGNMENT") | (Receipt.household_id.is_(None))
                )
            )
        ).scalar_one() or 0

        return {
            "users_count": users_count,
            "active_users_count": active_users_count,
            "households_count": households_count,
            "receipts_count": receipts_count,
            "pending_receipts_count": pending_receipts_count,
            "products_count": products_count,
            "total_spend": round(total_spend, 2),
            "active_registration_tokens_count": tokens_count,
        }

    # -------------------------------------------------------------
    # User Management
    # -------------------------------------------------------------
    @staticmethod
    async def list_all_users(db: AsyncSession) -> List[Dict]:
        """Lists all registered users with their household counts and status."""
        query = select(User).order_by(User.created_at.desc())
        res = await db.execute(query)
        users = res.scalars().all()

        user_list = []
        for u in users:
            # Count households membership
            hh_count_stmt = select(func.count(HouseholdMembership.id)).where(HouseholdMembership.user_id == u.id)
            hh_count = (await db.execute(hh_count_stmt)).scalar_one() or 0

            # Count imported receipts
            rc_count_stmt = select(func.count(Receipt.id)).where(Receipt.imported_by_user_id == u.id)
            rc_count = (await db.execute(rc_count_stmt)).scalar_one() or 0

            user_list.append({
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "is_superuser": u.is_superuser,
                "households_count": hh_count,
                "imported_receipts_count": rc_count,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            })
        return user_list

    @staticmethod
    async def update_user(db: AsyncSession, user_id: uuid.UUID, data: Dict) -> Dict:
        stmt = select(User).where(User.id == user_id)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

        if "full_name" in data and data["full_name"]:
            user.full_name = data["full_name"].strip()
        if "is_active" in data and data["is_active"] is not None:
            user.is_active = data["is_active"]
        if "is_superuser" in data and data["is_superuser"] is not None:
            user.is_superuser = data["is_superuser"]

        await db.commit()
        await db.refresh(user)

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
        }

    @staticmethod
    async def reset_user_password(db: AsyncSession, user_id: uuid.UUID, new_password: str) -> Dict:
        stmt = select(User).where(User.id == user_id)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

        user.hashed_password = hash_password(new_password)
        user.must_change_password = True
        user.failed_login_attempts = 0
        user.locked_until = None
        await db.commit()
        return {"status": "success", "message": f"Contraseña restablecida para {user.email}"}

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: uuid.UUID, current_superuser_id: uuid.UUID) -> Dict:
        if user_id == current_superuser_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes eliminar tu propia cuenta de superadministrador.")

        stmt = select(User).where(User.id == user_id)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

        await db.delete(user)
        await db.commit()
        return {"status": "success", "message": "Usuario eliminado correctamente."}

    # -------------------------------------------------------------
    # Household Management
    # -------------------------------------------------------------
    @staticmethod
    async def list_all_households(db: AsyncSession) -> List[Dict]:
        """Lists all households with member count, ticket count, and owner info."""
        query = select(Household).order_by(Household.created_at.desc())
        res = await db.execute(query)
        households = res.scalars().all()

        hh_list = []
        for h in households:
            # Get owner
            owner_stmt = (
                select(User)
                .join(HouseholdMembership, HouseholdMembership.user_id == User.id)
                .where(HouseholdMembership.household_id == h.id, HouseholdMembership.role == "OWNER")
            )
            owner = (await db.execute(owner_stmt)).scalar_one_or_none()

            # Member count
            m_count = (
                await db.execute(select(func.count(HouseholdMembership.id)).where(HouseholdMembership.household_id == h.id))
            ).scalar_one() or 0

            # Receipt count & spend
            r_stmt = select(func.count(Receipt.id), func.coalesce(func.sum(Receipt.total_amount), 0.0)).where(
                Receipt.household_id == h.id
            )
            r_res = (await db.execute(r_stmt)).first()
            r_count = r_res[0] or 0
            spend = float(r_res[1] or 0.0)

            hh_list.append({
                "id": str(h.id),
                "name": h.name,
                "currency": h.currency,
                "owner_email": owner.email if owner else "Sin propietario",
                "owner_name": owner.full_name if owner else None,
                "members_count": m_count,
                "receipts_count": r_count,
                "total_spend": round(spend, 2),
                "mercadona_online_enabled": bool(h.settings.get("mercadona_online_enabled", False)) if h.settings else False,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            })
        return hh_list

    @staticmethod
    async def update_household(db: AsyncSession, household_id: uuid.UUID, data: Dict) -> Dict:
        stmt = select(Household).where(Household.id == household_id)
        res = await db.execute(stmt)
        hh = res.scalar_one_or_none()
        if not hh:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hogar no encontrado.")

        if "name" in data and data["name"]:
            hh.name = data["name"].strip()
        if "currency" in data and data["currency"]:
            hh.currency = data["currency"].strip().upper()

        await db.commit()
        await db.refresh(hh)
        return {
            "id": str(hh.id),
            "name": hh.name,
            "currency": hh.currency,
        }

    @staticmethod
    async def delete_household(db: AsyncSession, household_id: uuid.UUID) -> Dict:
        stmt = select(Household).where(Household.id == household_id)
        res = await db.execute(stmt)
        hh = res.scalar_one_or_none()
        if not hh:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hogar no encontrado.")

        await db.delete(hh)
        await db.commit()
        return {"status": "success", "message": "Hogar eliminado correctamente."}

    # -------------------------------------------------------------
    # Registration Tokens Management
    # -------------------------------------------------------------
    @staticmethod
    async def list_registration_tokens(db: AsyncSession) -> List[Dict]:
        query = select(RegistrationToken).order_by(RegistrationToken.created_at.desc())
        res = await db.execute(query)
        tokens = res.scalars().all()

        return [
            {
                "id": str(t.id),
                "token": t.token,
                "note": t.note,
                "max_uses": t.max_uses,
                "times_used": t.times_used,
                "is_active": t.is_active,
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tokens
        ]

    @staticmethod
    async def create_registration_token(
        db: AsyncSession,
        creator_id: uuid.UUID,
        token: Optional[str] = None,
        note: Optional[str] = None,
        max_uses: int = 1,
        expires_in_days: Optional[int] = 30,
    ) -> Dict:
        if token and token.strip():
            token_str = token.strip().upper()
            existing_stmt = select(RegistrationToken).where(RegistrationToken.token == token_str)
            existing = (await db.execute(existing_stmt)).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El token '{token_str}' ya existe en el sistema.",
                )
        else:
            # Generate clean secure token, e.g. SUP-XXXX-XXXX
            chars = string.ascii_uppercase + string.digits
            part1 = "".join(secrets.choice(chars) for _ in range(4))
            part2 = "".join(secrets.choice(chars) for _ in range(4))
            token_str = f"SUP-{part1}-{part2}"

        expires_at = None
        if expires_in_days and expires_in_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        token_obj = RegistrationToken(
            token=token_str,
            note=note.strip() if note else "Invitación generada por Superadmin",
            max_uses=max(1, max_uses),
            times_used=0,
            is_active=True,
            expires_at=expires_at,
            created_by_user_id=creator_id,
        )
        db.add(token_obj)
        await db.commit()
        await db.refresh(token_obj)

        return {
            "id": str(token_obj.id),
            "token": token_obj.token,
            "note": token_obj.note,
            "max_uses": token_obj.max_uses,
            "times_used": token_obj.times_used,
            "is_active": token_obj.is_active,
            "expires_at": token_obj.expires_at.isoformat() if token_obj.expires_at else None,
            "created_at": token_obj.created_at.isoformat() if token_obj.created_at else None,
        }

    @staticmethod
    async def revoke_registration_token(db: AsyncSession, token_id: uuid.UUID) -> Dict:
        stmt = select(RegistrationToken).where(RegistrationToken.id == token_id)
        res = await db.execute(stmt)
        token_obj = res.scalar_one_or_none()
        if not token_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token no encontrado.")

        token_obj.is_active = False
        await db.commit()
        return {"status": "success", "message": "Token de registro revocado."}

    # -------------------------------------------------------------
    # System Settings & Google OAuth Configuration
    # -------------------------------------------------------------
    @staticmethod
    async def get_system_settings(db: AsyncSession) -> Dict[str, Any]:
        """Retrieves system settings, masking sensitive credentials and calculating the redirect URI."""
        from app.core.config import settings
        from app.domains.admin.models import SystemSetting
        from app.core.security import decrypt_secret
        from app.core.bootstrap import ensure_system_secrets

        await ensure_system_secrets(db)

        res = await db.execute(select(SystemSetting))
        settings_rows = res.scalars().all()
        settings_map = {row.key: row.value for row in settings_rows}

        server_public_url = settings_map.get("server_public_url") or settings.SERVER_PUBLIC_URL or "http://localhost:5173"
        server_public_url = server_public_url.rstrip("/")

        google_client_id = settings_map.get("google_client_id") or settings.GOOGLE_CLIENT_ID or ""

        # Secret handling
        raw_secret = settings_map.get("google_client_secret") or settings.GOOGLE_CLIENT_SECRET or ""
        google_client_secret_set = bool(raw_secret.strip())
        if google_client_secret_set:
            try:
                decrypted = decrypt_secret(raw_secret)
                secret_to_mask = decrypted
                if len(secret_to_mask) > 6:
                    masked = "••••••••••••" + secret_to_mask[-4:]
                else:
                    masked = "••••••••••••"
            except Exception:
                # Decryption failed (e.g. master key changed)
                if raw_secret.startswith("gAAAAA"):
                    masked = ""
                    google_client_secret_set = False
                else:
                    secret_to_mask = raw_secret
                    masked = "••••••••••••" + (secret_to_mask[-4:] if len(secret_to_mask) > 6 else "")
        else:
            masked = ""

        # Google Redirect URI dynamically calculated based on public server URL
        google_redirect_uri = f"{server_public_url}/integrations/google/callback"

        return {
            "server_public_url": server_public_url,
            "google_client_id": google_client_id,
            "google_client_secret_masked": masked,
            "google_client_secret_set": google_client_secret_set,
            "google_redirect_uri": google_redirect_uri,
        }

    @staticmethod
    async def update_system_settings(db: AsyncSession, data: Dict[str, Any]) -> Dict[str, Any]:
        """Persists updated system settings."""
        from app.domains.admin.models import SystemSetting
        from app.core.security import encrypt_secret
        from app.core.bootstrap import ensure_system_secrets

        await ensure_system_secrets(db)

        # 1. Server Public URL
        if "server_public_url" in data and data["server_public_url"] is not None:
            clean_url = str(data["server_public_url"]).strip().rstrip("/")
            if clean_url:
                stmt = select(SystemSetting).where(SystemSetting.key == "server_public_url")
                row = (await db.execute(stmt)).scalar_one_or_none()
                if not row:
                    row = SystemSetting(key="server_public_url", value=clean_url, description="URL pública base del servidor", is_secret=False)
                    db.add(row)
                else:
                    row.value = clean_url

        # 2. Google Client ID
        if "google_client_id" in data and data["google_client_id"] is not None:
            clean_client_id = str(data["google_client_id"]).strip()
            stmt = select(SystemSetting).where(SystemSetting.key == "google_client_id")
            row = (await db.execute(stmt)).scalar_one_or_none()
            if not row:
                row = SystemSetting(key="google_client_id", value=clean_client_id, description="Google OAuth 2.0 Client ID", is_secret=False)
                db.add(row)
            else:
                row.value = clean_client_id

        # 3. Google Client Secret (only update if provided and not masked)
        if "google_client_secret" in data and data["google_client_secret"]:
            raw_secret = str(data["google_client_secret"]).strip()
            if not raw_secret.startswith("••"):
                encrypted_val = encrypt_secret(raw_secret)
                stmt = select(SystemSetting).where(SystemSetting.key == "google_client_secret")
                row = (await db.execute(stmt)).scalar_one_or_none()
                if not row:
                    row = SystemSetting(key="google_client_secret", value=encrypted_val, description="Google OAuth 2.0 Client Secret", is_secret=True)
                    db.add(row)
                else:
                    row.value = encrypted_val

        await db.commit()
        return await AdminService.get_system_settings(db)

    @staticmethod
    async def get_effective_google_config(db: Optional[AsyncSession] = None) -> Tuple[str, str, str]:
        """
        Returns (client_id, client_secret, redirect_uri) for Google OAuth.
        Prefers database settings; falls back to environment configuration.
        """
        from app.core.config import settings
        from app.core.security import decrypt_secret

        client_id = settings.GOOGLE_CLIENT_ID
        client_secret = settings.GOOGLE_CLIENT_SECRET
        server_url = settings.SERVER_PUBLIC_URL or "http://localhost:5173"
        redirect_uri = settings.GOOGLE_REDIRECT_URI

        if db:
            from app.domains.admin.models import SystemSetting
            from app.core.bootstrap import ensure_system_secrets
            await ensure_system_secrets(db)

            res = await db.execute(select(SystemSetting))
            settings_rows = res.scalars().all()
            settings_map = {row.key: row.value for row in settings_rows}

            if settings_map.get("google_client_id"):
                client_id = settings_map["google_client_id"]

            if settings_map.get("google_client_secret"):
                raw_secret = settings_map["google_client_secret"]
                try:
                    client_secret = decrypt_secret(raw_secret)
                except Exception:
                    if raw_secret.startswith("gAAAAA"):
                        raise ValueError(
                            "No se pudo descifrar el Client Secret de Google almacenado porque la clave maestra "
                            "(ENCRYPTION_MASTER_KEY) ha cambiado o no coincide. "
                            "Por favor, ve a Administración > Ajustes y vuelve a introducir tu Client Secret."
                        )
                    client_secret = raw_secret

            if settings_map.get("server_public_url"):
                server_url = settings_map["server_public_url"].rstrip("/")
                redirect_uri = f"{server_url}/integrations/google/callback"

        return client_id, client_secret, redirect_uri

