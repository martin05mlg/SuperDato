from typing import List, Optional
from pydantic import BaseModel


class ReceiptLineResponse(BaseModel):
    id: str
    line_order: int
    raw_description: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    category_name: Optional[str] = None
    quantity: float
    unit_of_measure: str
    unit_price: float
    discount_amount: float = 0.0
    line_total: float
    is_weighed_item: bool = False
    weight_in_kg: Optional[float] = None
    validation_status: str = "VALID"
    is_manual_override: bool = False
    image_url: Optional[str] = None
    brand: Optional[str] = None
    enriched_name: Optional[str] = None
    packaging: Optional[str] = None
    price_change_pct: Optional[float] = None
    previous_unit_price: Optional[float] = None


class ReceiptLineUpdate(BaseModel):
    raw_description: Optional[str] = None
    product_name: Optional[str] = None
    product_id: Optional[str] = None
    category_name: Optional[str] = None
    quantity: Optional[float] = None
    unit_of_measure: Optional[str] = None
    unit_price: Optional[float] = None
    discount_amount: Optional[float] = None
    line_total: Optional[float] = None


class ReceiptTaxLineResponse(BaseModel):
    id: str
    tax_rate_percent: float
    taxable_base: float
    tax_amount: float
    total_with_tax: float


class ReceiptResponse(BaseModel):
    id: str
    household_id: Optional[str] = None
    company_name: str
    company_cif: str
    store_address: Optional[str] = None
    store_city: Optional[str] = None
    store_postal_code: Optional[str] = None
    invoice_number: str
    store_code: Optional[str] = None
    purchase_datetime: str
    purchase_date: str
    total_amount: float
    payment_method: Optional[str] = None
    card_last_four: Optional[str] = None
    status: str
    assignment_status: Optional[str] = "ASSIGNED"
    extraction_warnings: List[str] = []
    is_manual_override: bool = False
    lines_count: int = 0
    created_at: str


class ReceiptUpdate(BaseModel):
    household_id: Optional[str] = None
    store_address: Optional[str] = None
    store_city: Optional[str] = None
    store_postal_code: Optional[str] = None
    purchase_date: Optional[str] = None
    total_amount: Optional[float] = None
    payment_method: Optional[str] = None
    status: Optional[str] = None


class ReceiptAssignHouseholdRequest(BaseModel):
    household_id: str


class ReceiptBulkAssignRequest(BaseModel):
    receipt_ids: List[str]
    household_id: str


class ManualReceiptLineCreate(BaseModel):
    raw_description: str
    product_id: Optional[str] = None
    quantity: float = 1.0
    unit_of_measure: str = "ud"
    unit_price: float
    discount_amount: float = 0.0
    tax_rate_percent: float = 10.0
    is_weighed_item: bool = False
    weight_in_kg: Optional[float] = None


class ManualReceiptCreate(BaseModel):
    household_id: str
    purchase_datetime: Optional[str] = None
    invoice_number: Optional[str] = None
    store_address: Optional[str] = None
    store_city: Optional[str] = None
    store_postal_code: Optional[str] = None
    payment_method: Optional[str] = "TARJETA"
    lines: List[ManualReceiptLineCreate]


class ReceiptDetailResponse(ReceiptResponse):
    lines: List[ReceiptLineResponse] = []
    tax_lines: List[ReceiptTaxLineResponse] = []


from app.domains.analytics.schemas import (
    AnalyticsSummaryResponse,
    CategoryDistributionResponse,
    SpendingPointResponse,
    TopProductResponse,
)
