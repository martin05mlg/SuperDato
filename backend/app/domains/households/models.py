import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.core.database import Base, TimestampMixin


class Household(Base, TimestampMixin):
    """Household (multi-tenant household group) entity."""
    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="EUR",
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    memberships: Mapped[List["HouseholdMembership"]] = relationship(
        "HouseholdMembership",
        back_populates="household",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[List["HouseholdInvitation"]] = relationship(
        "HouseholdInvitation",
        back_populates="household",
        cascade="all, delete-orphan",
    )


class HouseholdMembership(Base):
    """Many-to-many relationship linking a user to a household with a defined role."""
    __tablename__ = "household_memberships"
    __table_args__ = (
        UniqueConstraint("household_id", "user_id", name="uq_household_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="MEMBER",  # OWNER, ADMIN, MEMBER
        nullable=False,
    )
    custom_permissions: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    household: Mapped["Household"] = relationship("Household", back_populates="memberships")
    user: Mapped["app.domains.auth.models.User"] = relationship("app.domains.auth.models.User", back_populates="memberships")


class HouseholdInvitation(Base):
    """Pending email invitations to join a household."""
    __tablename__ = "household_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="MEMBER",
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",  # PENDING, ACCEPTED, REVOKED, EXPIRED
        nullable=False,
    )
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    household: Mapped["Household"] = relationship("Household", back_populates="invitations")

