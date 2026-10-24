import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.core.database import Base, TimestampMixin


class GoogleAccountConnection(Base, TimestampMixin):
    """Google OAuth 2.0 account connection linked to a user and household."""
    __tablename__ = "google_account_connections"
    __table_args__ = (
        UniqueConstraint("household_id", "google_email", name="uq_household_google_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    google_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    encrypted_tokens: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    scopes: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    initial_sync_date: Mapped[date] = mapped_column(
        Date,
        default=lambda: datetime.now(timezone.utc).date(),
        nullable=False,
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_history_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    sync_status: Mapped[str] = mapped_column(
        String(30),
        default="IDLE",  # IDLE, SYNCING, ERROR, NEEDS_REAUTH
        nullable=False,
    )
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "app.domains.auth.models.User",
        foreign_keys=[user_id],
        lazy="selectin",
    )
    import_jobs: Mapped[List["ImportJob"]] = relationship(
        "ImportJob",
        back_populates="connection",
        cascade="all, delete-orphan",
    )

    @property
    def user_email(self) -> Optional[str]:
        return self.user.email if self.user else None

    @property
    def user_full_name(self) -> Optional[str]:
        return self.user.full_name if self.user else None


class ImportJob(Base):
    """Tracks an import job execution (manual upload, periodic Gmail sync, etc.)."""
    __tablename__ = "import_jobs"

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
    connection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("google_account_connections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,  # GMAIL_PERIODIC, GMAIL_MANUAL, PDF_UPLOAD
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",  # PENDING, PROCESSING, COMPLETED, FAILED
        nullable=False,
    )
    messages_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    receipts_imported: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    receipts_skipped: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    errors_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_details: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    connection: Mapped[Optional["GoogleAccountConnection"]] = relationship(
        "GoogleAccountConnection",
        back_populates="import_jobs",
    )

