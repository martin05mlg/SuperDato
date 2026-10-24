"""Arranque inicial: creación segura del superadministrador (sin credenciales públicas conocidas)."""
import logging
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.config import settings
from app.core.password_policy import validate_password_strength
from app.core.security import hash_password

logger = logging.getLogger("superdato.bootstrap")


def _announce(email: str, password: str) -> None:
    banner = (
        "\n" + "=" * 68 + "\n"
        "  SUPERDATO · CREDENCIALES INICIALES DEL SUPERADMINISTRADOR\n"
        "  (se muestran UNA sola vez; cámbiala en el primer inicio de sesión)\n\n"
        f"    Usuario:    {email}\n"
        f"    Contraseña: {password}\n\n"
        "  Si la pierdes: docker compose exec api python scripts/reset_admin.py\n"
        + "=" * 68 + "\n"
    )
    print(banner, flush=True)


async def ensure_superadmin(session: AsyncSession) -> None:
    """Crea el superadmin SOLO si no existe ninguno. Nunca pisa contraseñas ni desbloquea cuentas."""
    from app.domains.auth.models import User
    from app.domains.households.models import Household, HouseholdMembership

    email = settings.SUPERADMIN_EMAIL.lower().strip()

    existing_super = (
        await session.execute(select(User).where(User.is_superuser == True).limit(1))  # noqa: E712
    ).scalar_one_or_none()
    if existing_super:
        return

    configured = settings.SUPERADMIN_PASSWORD
    if not configured:
        logger.info("SUPERADMIN_PASSWORD no está definida. La instancia se inicializará mediante First-Run Web Setup.")
        return

    password = configured
    must_change = False
    try:
        validate_password_strength(configured, email)
    except ValueError as exc:
        logger.warning("SUPERADMIN_PASSWORD no cumple la política (%s); se exigirá cambiarla.", exc)
        must_change = True

    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user:
        # Existe un usuario con ese email (registrado antes): se promociona sin tocar su contraseña
        user.is_superuser = True
        user.is_active = True
        await session.commit()
        audit("superadmin_promoted", target=email)
        return

    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password(password),
        full_name="Superadministrador",
        is_active=True,
        is_verified=True,
        is_superuser=True,
        must_change_password=must_change,
    )
    session.add(user)
    await session.flush()

    household = Household(
        id=uuid.uuid4(),
        name=f"Hogar de {user.full_name}",
        currency="EUR",
        created_by_user_id=user.id,
    )
    session.add(household)
    await session.flush()
    session.add(
        HouseholdMembership(id=uuid.uuid4(), household_id=household.id, user_id=user.id, role="OWNER")
    )
    await session.commit()
    audit("superadmin_created", target=email, generated_password=False)

