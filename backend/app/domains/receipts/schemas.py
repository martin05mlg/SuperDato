from typing import List, Optional
from pydantic import BaseModel


class ReceiptLineResponse(BaseModel):
    id: str
    line_order: int
    raw_description: str
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


class ReceiptTaxLineResponse(BaseModel):
    id: str
    tax_rate_percent: float
    taxable_base: float
    tax_amount: float
    total_with_tax: float


class ReceiptResponse(BaseModel):
    id: str
    household_id: str
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
    extraction_warnings: List[str] = []
    is_manual_override: bool = False
    lines_count: int = 0
    created_at: str


class ReceiptDetailResponse(ReceiptResponse):
    lines: List[ReceiptLineResponse] = []
    tax_lines: List[ReceiptTaxLineResponse] = []


class AnalyticsSummaryResponse(BaseModel):
    total_spend: float
    previous_spend: float
    spend_variation_pct: float
    receipt_count: int
    average_ticket: float
    median_ticket: float
    last_purchase_date: Optional[str] = None
    last_sync_at: Optional[str] = None


class CategoryDistributionResponse(BaseModel):
    category_name: str
    color_hex: str
    total_spend: float
    percentage: float


class SpendingPointResponse(BaseModel):
    date: str
    total_amount: float
    receipt_count: int

