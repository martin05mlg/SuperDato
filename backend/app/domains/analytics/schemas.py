from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class AnalyticsSummaryResponse(BaseModel):
    total_spend: float
    previous_spend: float
    spend_variation_pct: float
    receipt_count: int
    average_ticket: float
    median_ticket: float
    total_items_count: int = 0
    last_purchase_date: Optional[str] = None
    last_sync_at: Optional[str] = None
    period_label: Optional[str] = None


class CategoryDistributionResponse(BaseModel):
    category_name: str
    color_hex: str
    total_spend: float
    percentage: float
    items_count: int = 0


class SpendingPointResponse(BaseModel):
    date: str
    total_amount: float
    receipt_count: int


class TopProductResponse(BaseModel):
    product_id: Optional[str] = None
    product_name: str
    category_name: str
    total_spend: float
    total_quantity: float
    purchases_count: int
    average_price: float

