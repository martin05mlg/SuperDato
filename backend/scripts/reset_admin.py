"""CLI utility to reset or unlock the SuperAdmin account in SuperDato.

Usage inside Docker:
    docker compose exec api python scripts/reset_admin.py
    docker compose exec api python scripts/reset_admin.py --password "YourNewStrongPassword123!"
"""
import argparse
import asyncio
import os
import secrets
import string
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import async_session  # noqa: E402
from app.core.password_policy import validate_password_strength  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.domains.auth.models import User  # noqa: E402


def _generate_random_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#%^&*-_=+"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#%^&*-_=+" for c in pwd)
        ):
            return pwd


async def reset_superadmin(email: str | None, password: str | None) -> int:
    target_email = (email or settings.SUPERADMIN_EMAIL).strip().lower()
    generated = False
    if password:
        new_password = validate_password_strength(password)
    else:
        new_password = _generate_random_password()
        generated = True

    async with async_session() as db:
        res = await db.execute(select(User).where(User.email == target_email))
        user = res.scalar_one_or_none()
        if not user:
            res = await db.execute(select(User).where(User.is_superuser.is_(True)).limit(1))
            user = res.scalar_one_or_none()

        if not user:
            print(f"[ERROR] No se encontró ningún usuario administrador ({target_email}).", file=sys.stderr)
            return 1

        user.hashed_password = get_password_hash(new_password)
        user.is_active = True
        user.is_superuser = True
        user.failed_login_attempts = 0
        user.locked_until = None
        user.must_change_password = generated
        await db.commit()

        banner = (
            "\n"
            "========================================================================\n"
            "  SUPERDATO — CREDENCIALES DE SUPERADMIN RESTABLECIDAS\n"
            "========================================================================\n"
            f"  Email      : {user.email}\n"
            f"  Contraseña : {new_password}\n"
            "========================================================================\n"
        )
        print(banner, flush=True)
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Restablece y desbloquea la cuenta SuperAdmin de SuperDato.")
    parser.add_argument("--email", help="Email del administrador (por defecto SUPERADMIN_EMAIL)", default=None)
    parser.add_argument("--password", help="Nueva contraseña (si se omite, se genera una aleatoria)", default=None)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(reset_superadmin(args.email, args.password)))


if __name__ == "__main__":
    main()

