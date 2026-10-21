import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User account entity."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    memberships: Mapped[List["HouseholdMembership"]] = relationship(
        "HouseholdMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )

