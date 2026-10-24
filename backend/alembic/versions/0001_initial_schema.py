"""Initial schema for SuperDato

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-24 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import inspect, text

from app.core.database import Base
import app.domains.auth.models  # noqa: F401
import app.domains.households.models  # noqa: F401
import app.domains.catalog.models  # noqa: F401
import app.domains.receipts.models  # noqa: F401
import app.domains.integrations.models  # noqa: F401
import app.domains.shopping.models  # noqa: F401
import app.domains.admin.models  # noqa: F401

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    # Ensure incremental column `must_change_password` exists on pre-existing `users` table
    inspector = inspect(bind)
    if "users" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("users")}
        if "must_change_password" not in cols:
            op.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT FALSE"))


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

