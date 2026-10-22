import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- Category Schemas ---

class CategoryBase(BaseModel):
    name: str
    slug: str
    icon: Optional[str] = None
    color_hex: Optional[str] = None
    is_system: bool = True
    parent_id: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: str
    product_count: int = 0
    model_config = ConfigDict(from_attributes=True)


# --- Product Schemas ---

class ProductBase(BaseModel):
    canonical_name: str
    category_id: str
    default_unit: str = "ud"
    format_description: Optional[str] = None


class ProductCreate(ProductBase):
    initial_alias: Optional[str] = None


class ProductUpdate(BaseModel):
    canonical_name: Optional[str] = None
    category_id: Optional[str] = None
    default_unit: Optional[str] = None
    format_description: Optional[str] = None


class ProductAliasResponse(BaseModel):
    id: str
    product_id: str
    raw_name_normalized: str
    source: str
    is_verified: bool
    model_config = ConfigDict(from_attributes=True)


class ProductAliasCreate(BaseModel):
    raw_name_normalized: str
    source: str = "MERCADONA"


class ProductResponse(ProductBase):
    id: str
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    latest_price: Optional[float] = None
    latest_price_per_kg_or_l: Optional[float] = None
    latest_date: Optional[str] = None
    observations_count: int = 0
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    aliases: List[str] = []
    created_at: str
    # Mercadona Online enrichment attributes
    mercadona_online_id: Optional[str] = None
    enriched_name: Optional[str] = None
    image_url: Optional[str] = None
    brand: Optional[str] = None
    packaging: Optional[str] = None
    mercadona_url: Optional[str] = None
    enrichment_status: Optional[str] = None
    enrichment_confidence: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)


# --- Mercadona Online Schemas ---

class MercadonaOnlineProductResponse(BaseModel):
    id: str
    display_name: str
    slug: Optional[str] = None
    brand: Optional[str] = None
    packaging: Optional[str] = None
    thumbnail_url: Optional[str] = None
    share_url: Optional[str] = None
    unit_price: Optional[float] = None
    reference_price: Optional[float] = None
    reference_format: Optional[str] = None
    category_path: Optional[str] = None
    warehouse_code: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class MercadonaSyncRequest(BaseModel):
    postal_code: Optional[str] = None
    limit_subcategories: Optional[int] = None


class MercadonaSyncResponse(BaseModel):
    warehouse_code: str
    subcategories_processed: int
    products_upserted: int
    synced_at: str


class MercadonaEnrichRequest(BaseModel):
    auto_threshold: float = 0.85


class MercadonaEnrichResponse(BaseModel):
    total_products_checked: int
    auto_enriched_count: int
    pending_suggestions_count: int
    threshold_used: float


class MercadonaCandidateItem(BaseModel):
    mercadona_product: MercadonaOnlineProductResponse
    score: float
    price_match: bool = False


class MercadonaSuggestionItem(BaseModel):
    product: ProductResponse
    candidates: List[MercadonaCandidateItem]


class MercadonaConfirmMatchRequest(BaseModel):
    product_id: str
    mercadona_online_id: Optional[str] = None
    url_or_id: Optional[str] = None


class MercadonaRejectMatchRequest(BaseModel):
    product_id: str


# --- Price Observation Schemas ---

class PriceObservationResponse(BaseModel):
    id: str
    household_id: str
    product_id: str
    receipt_line_id: str
    observed_at: str
    observed_date: str
    unit_price: float
    price_per_kg_or_l: Optional[float] = None
    store_code: Optional[str] = None
    raw_description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class PriceHistoryResponse(BaseModel):
    product_id: str
    product_name: str
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    default_unit: str
    current_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    observations: List[PriceObservationResponse] = []

