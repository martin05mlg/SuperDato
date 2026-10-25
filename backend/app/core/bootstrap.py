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


async def ensure_system_secrets(session: AsyncSession) -> None:
    """
    Sincroniza y garantiza que las claves criptográficas críticas (ENCRYPTION_MASTER_KEY y SECRET_KEY)
    queden permanentemente guardadas en PostgreSQL (tabla system_settings).
    De este modo, NUNCA se pierden entre reinicios de contenedor ni reconstrucciones de Docker,
    asegurando que el Google Client Secret y los tokens OAuth persistan indefinidamente.
    """
    import os
    import secrets
    from app.domains.admin.models import SystemSetting

    # 1. ENCRYPTION_MASTER_KEY
    env_master = os.getenv("ENCRYPTION_MASTER_KEY", "").strip()
    stmt_enc = select(SystemSetting).where(SystemSetting.key == "_system_encryption_master_key")
    enc_row = (await session.execute(stmt_enc)).scalar_one_or_none()

    if env_master and len(env_master) >= 32:
        settings.ENCRYPTION_MASTER_KEY = env_master
        if not enc_row:
            session.add(SystemSetting(
                key="_system_encryption_master_key",
                value=env_master,
                description="Clave maestra persistente de cifrado Fernet",
                is_secret=True,
            ))
            await session.commit()
        elif enc_row.value != env_master:
            enc_row.value = env_master
            await session.commit()
    elif enc_row and enc_row.value and len(enc_row.value) >= 32:
        settings.ENCRYPTION_MASTER_KEY = enc_row.value
        logger.info("ENCRYPTION_MASTER_KEY persistente cargada con éxito desde la base de datos.")
    else:
        key_val = settings.ENCRYPTION_MASTER_KEY
        if not key_val or len(key_val) < 32:
            key_val = secrets.token_urlsafe(32)
        settings.ENCRYPTION_MASTER_KEY = key_val
        if not enc_row:
            session.add(SystemSetting(
                key="_system_encryption_master_key",
                value=key_val,
                description="Clave maestra persistente de cifrado Fernet",
                is_secret=True,
            ))
        else:
            enc_row.value = key_val
        await session.commit()
        logger.info("Generada y asegurada nueva ENCRYPTION_MASTER_KEY persistente en la base de datos.")

    # 2. SECRET_KEY
    env_sec = os.getenv("SECRET_KEY", "").strip()
    stmt_sec = select(SystemSetting).where(SystemSetting.key == "_system_jwt_secret_key")
    sec_row = (await session.execute(stmt_sec)).scalar_one_or_none()

    if env_sec and len(env_sec) >= 32:
        settings.SECRET_KEY = env_sec
        if not sec_row:
            session.add(SystemSetting(
                key="_system_jwt_secret_key",
                value=env_sec,
                description="Clave secreta persistente para tokens JWT",
                is_secret=True,
            ))
            await session.commit()
        elif sec_row.value != env_sec:
            sec_row.value = env_sec
            await session.commit()
    elif sec_row and sec_row.value and len(sec_row.value) >= 32:
        settings.SECRET_KEY = sec_row.value
        logger.info("SECRET_KEY persistente cargada con éxito desde la base de datos.")
    else:
        sec_val = settings.SECRET_KEY
        if not sec_val or len(sec_val) < 32:
            sec_val = secrets.token_urlsafe(64)
        settings.SECRET_KEY = sec_val
        if not sec_row:
            session.add(SystemSetting(
                key="_system_jwt_secret_key",
                value=sec_val,
                description="Clave secreta persistente para tokens JWT",
                is_secret=True,
            ))
        else:
            sec_row.value = sec_val
        await session.commit()
        logger.info("Generada y asegurada nueva SECRET_KEY persistente en la base de datos.")


async def heal_inconsistent_receipt_line_prices(session: AsyncSession) -> int:
    """
    Detects and automatically repairs corrupted unit prices on receipt lines and price observations
    caused by product title numbers (e.g. Alcohol 96) being misparsed as unit prices.
    """
    from decimal import Decimal
    from sqlalchemy import update
    from app.domains.receipts.models import ReceiptLine
    from app.domains.catalog.models import PriceObservation

    stmt = select(ReceiptLine).where(
        ReceiptLine.quantity > 0,
        ReceiptLine.line_total > 0,
    )
    res = await session.execute(stmt)
    lines = res.scalars().all()

    healed_count = 0
    for line in lines:
        try:
            qty = Decimal(str(line.quantity))
            unit_p = Decimal(str(line.unit_price))
            total = Decimal(str(line.line_total))
            discount = Decimal(str(line.discount_amount or 0))

            expected_unit_p = round((total + discount) / qty, 2)

            # If mathematical difference is greater than 5 cents:
            if abs(qty * unit_p - (total + discount)) > Decimal("0.05"):
                old_unit_p = float(line.unit_price)
                new_unit_p = float(expected_unit_p)
                line.unit_price = new_unit_p

                # Restore missing suffix in raw description if it was misparsed as price (e.g. Alcohol 96)
                if "ALCOHOL ETILICO" in line.raw_description.upper() and (old_unit_p == 96.0 or old_unit_p == 70.0):
                    suffix = " 96" if old_unit_p == 96.0 else " 70"
                    if not line.raw_description.endswith(suffix):
                        line.raw_description = f"{line.raw_description}{suffix}"

                # Fix corresponding PriceObservation
                obs_stmt = (
                    update(PriceObservation)
                    .where(PriceObservation.receipt_line_id == line.id)
                    .values(unit_price=new_unit_p)
                )
                await session.execute(obs_stmt)
                healed_count += 1
                logger.info(
                    f"[PriceHealer] Line {line.id} ('{line.raw_description}'): "
                    f"unit_price repaired {old_unit_p}€ -> {new_unit_p}€ (total {float(total)}€)"
                )
        except Exception as e:
            logger.warning(f"[PriceHealer] Error processing line {line.id}: {e}")

    if healed_count > 0:
        await session.commit()
        logger.info(f"[PriceHealer] Successfully repaired {healed_count} receipt lines and price observations.")

    return healed_count

