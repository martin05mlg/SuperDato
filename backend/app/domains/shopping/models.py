import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class ShoppingListItem(Base, TimestampMixin):
    """Shopping list item scoped to a household."""
    __tablename__ = "shopping_list_items"

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
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(10, 3),
        default=1.0,
        nullable=False,
    )
    unit_of_measure: Mapped[str] = mapped_column(
        String(10),
        default="ud",
        nullable=False,
    )
    estimated_unit_price: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    is_checked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    household = relationship("Household")
    product = relationship("Product")

