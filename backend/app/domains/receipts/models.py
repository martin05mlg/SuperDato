import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.core.database import Base, TimestampMixin


class Receipt(Base, TimestampMixin):
    """Mercadona digital receipt root entity."""
    __tablename__ = "receipts"

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
    imported_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    import_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("import_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_name: Mapped[str] = mapped_column(
        String(100),
        default="MERCADONA, S.A.",
        nullable=False,
    )
    company_cif: Mapped[str] = mapped_column(
        String(20),
        default="A-46103834",
        nullable=False,
    )
    store_address: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    store_postal_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    store_city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    store_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )
    pos_register: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    purchase_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    purchase_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    purchase_time: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    total_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    discounts_total: Mapped[float] = mapped_column(
        Numeric(10, 2),
        default=0.00,
        nullable=False,
    )
    payment_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    card_last_four: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
    )
    deduplication_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="PROCESSED",  # PENDING, PROCESSED, REVISION_NEEDED, ERROR
        nullable=False,
    )
    extraction_warnings: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    raw_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    is_manual_override: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    lines: Mapped[List["ReceiptLine"]] = relationship(
        "ReceiptLine",
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="ReceiptLine.line_order",
    )
    tax_lines: Mapped[List["ReceiptTaxLine"]] = relationship(
        "ReceiptTaxLine",
        back_populates="receipt",
        cascade="all, delete-orphan",
    )


class ReceiptTaxLine(Base):
    """Breakdown of indirect tax rates (IVA 4%, 10%, 21%)."""
    __tablename__ = "receipt_tax_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tax_rate_percent: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    taxable_base: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    tax_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    total_with_tax: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # Relationship
    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="tax_lines")


class ReceiptLine(Base):
    """Individual line item from a Mercadona ticket."""
    __tablename__ = "receipt_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    raw_description: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(10, 3),
        nullable=False,
    )
    unit_of_measure: Mapped[str] = mapped_column(
        String(10),
        default="ud",
        nullable=False,
    )
    unit_price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    discount_amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        default=0.00,
        nullable=False,
    )
    line_total: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    is_weighed_item: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    weight_in_kg: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 3),
        nullable=True,
    )
    validation_status: Mapped[str] = mapped_column(
        String(20),
        default="VALID",  # VALID, MANUALLY_EDITED, SUSPICIOUS
        nullable=False,
    )
    raw_line_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    is_manual_override: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="lines")
    product: Mapped[Optional["app.domains.catalog.models.Product"]] = relationship(
        "app.domains.catalog.models.Product",
        back_populates="receipt_lines",
    )
    price_observation: Mapped[Optional["app.domains.catalog.models.PriceObservation"]] = relationship(
        "app.domains.catalog.models.PriceObservation",
        back_populates="receipt_line",
        uselist=False,
        cascade="all, delete-orphan",
    )
