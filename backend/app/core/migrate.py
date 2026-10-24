"""Migraciones automáticas de esquema con Alembic al arrancar la API.

- Base de datos nueva            -> `alembic upgrade head`
- Base creada antes de Alembic   -> se completa lo que falte y se hace `stamp head`
- Base ya versionada             -> `alembic upgrade head`
"""
import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.database import engine

logger = logging.getLogger("superdato.migrate")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def _detect_state(sync_conn) -> dict:
    insp = inspect(sync_conn)
    tables = set(insp.get_table_names())
    state = {"has_version": "alembic_version" in tables, "has_users": "users" in tables, "missing_columns": []}
    if state["has_users"]:
        cols = {c["name"] for c in insp.get_columns("users")}
        if "must_change_password" not in cols:
            state["missing_columns"].append("must_change_password")
    return state


async def _prepare_legacy(state: dict) -> None:
    """Completa columnas añadidas tras crear el esquema con create_all (instalaciones previas)."""
    if "must_change_password" in state["missing_columns"]:
        async with engine.begin() as conn:
            default = "FALSE" if conn.dialect.name == "postgresql" else "0"
            await conn.execute(
                text(f"ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT {default}")
            )


async def run_migrations() -> None:
    """Aplica las migraciones pendientes (idempotente)."""
    async with engine.connect() as conn:
        state = await conn.run_sync(_detect_state)

    cfg = _alembic_config()
    if state["has_users"] and not state["has_version"]:
        logger.warning("Base de datos previa a Alembic detectada: se actualiza esquema y versiona.")
        await _prepare_legacy(state)

    await asyncio.to_thread(command.upgrade, cfg, "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migrations())

