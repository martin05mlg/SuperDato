"""Support multiple email connections per household

Revision ID: 0002_multi_user_connections
Revises: 0001_initial
Create Date: 2026-10-24 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import inspect

revision: str = "0002_multi_user_connections"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "google_account_connections" in inspector.get_table_names():
        constraints = [c["name"] for c in inspector.get_unique_constraints("google_account_connections")]
        if "uq_user_google_email" in constraints:
            try:
                op.drop_constraint("uq_user_google_email", "google_account_connections", type_="unique")
            except Exception:
                pass
        if "uq_household_google_email" not in constraints:
            try:
                op.create_unique_constraint("uq_household_google_email", "google_account_connections", ["household_id", "google_email"])
            except Exception:
                pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "google_account_connections" in inspector.get_table_names():
        constraints = [c["name"] for c in inspector.get_unique_constraints("google_account_connections")]
        if "uq_household_google_email" in constraints:
            try:
                op.drop_constraint("uq_household_google_email", "google_account_connections", type_="unique")
            except Exception:
                pass

