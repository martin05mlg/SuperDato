import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base, TimestampMixin


class Category(Base):
    """Product category hierarchy for expense classification."""
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    icon: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    color_hex: Mapped[Optional[str]] = mapped_column(
        String(7),
        nullable=True,
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[List["Category"]] = relationship(
        "Category",
        back_populates="parent",
    )
    products: Mapped[List["Product"]] = relationship(
        "Product",
        back_populates="category",
    )


class Product(Base, TimestampMixin):
    """Canonical product in the centralized master catalog."""
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    canonical_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    default_unit: Mapped[str] = mapped_column(
        String(10),
        default="ud",  # 'ud', 'kg', 'pack'
        nullable=False,
    )
    format_description: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Mercadona Online Enrichment fields
    mercadona_online_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    enriched_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    brand: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    packaging: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    mercadona_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    enrichment_status: Mapped[str] = mapped_column(
        String(30),
        default="NONE",  # 'NONE', 'AUTO', 'MANUALLY_CONFIRMED'
        nullable=False,
    )
    enrichment_confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(4, 3),
        nullable=True,
    )

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="products",
    )
    aliases: Mapped[List["ProductAlias"]] = relationship(
        "ProductAlias",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    price_observations: Mapped[List["PriceObservation"]] = relationship(
        "PriceObservation",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    receipt_lines: Mapped[List["ReceiptLine"]] = relationship(
        "ReceiptLine",
        back_populates="product",
    )


class ProductAlias(Base):
    """Mapping from raw ticket receipt descriptions to canonical products."""
    __tablename__ = "product_aliases"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_name_normalized: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(30),
        default="MERCADONA",
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="aliases",
    )


class PriceObservation(Base):
    """
    Immutable historical price observation linked 1:1 to a receipt line.
    Enables inflation tracking, supermarket price evolution and analytics.
    """
    __tablename__ = "price_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    household_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receipt_line_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("receipt_lines.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    observed_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    unit_price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    price_per_kg_or_l: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    store_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="price_observations",
    )
    receipt_line: Mapped["ReceiptLine"] = relationship(
        "ReceiptLine",
        back_populates="price_observation",
    )


class MercadonaOnlineProduct(Base, TimestampMixin):
    """Snapshot of products cached from Mercadona Online Storefront."""
    __tablename__ = "mercadona_online_products"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,  # Mercadona online product ID, ej. "34210"
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    brand: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    packaging: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    thumbnail_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    share_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    reference_price: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 3),
        nullable=True,
    )
    reference_format: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    unit_price: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    category_path: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    warehouse_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )
    raw_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# Register receipts models in DeclarativeBase registry
import app.domains.receipts.models  # noqa: F401



