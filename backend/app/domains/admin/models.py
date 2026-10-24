import uuid
from typing import Optional
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, TimestampMixin


class SystemSetting(Base, TimestampMixin):
    """
    Global system configuration settings manageable dynamically by superadmins.
    Allows runtime configuration of OAuth credentials, server URLs, and platform parameters.
    """
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        index=True,
    )
    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    is_secret: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

