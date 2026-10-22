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
    comparison_label: Optional[str] = None
    max_ticket_amount: Optional[float] = None
    min_ticket_amount: Optional[float] = None
    shopping_frequency_days: Optional[float] = None
    monthly_average_spend: Optional[float] = None


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
    image_url: Optional[str] = None
    enriched_name: Optional[str] = None
    brand: Optional[str] = None


class WeekdayDistributionItem(BaseModel):
    day_name: str
    day_number: int
    receipt_count: int
    total_spend: float
    percentage: float


class StoreDistributionItem(BaseModel):
    store_name: str
    city: Optional[str] = None
    receipt_count: int
    total_spend: float
    percentage: float


class TaxBreakdownItem(BaseModel):
    tax_rate_percent: float
    taxable_base: float
    tax_amount: float
    total_with_tax: float
    percentage_of_tax: float


class BasketCompositionItem(BaseModel):
    group_name: str
    description: str
    icon: str
    color_hex: str
    total_spend: float
    percentage: float
    items_count: int


class HouseholdHabitsResponse(BaseModel):
    weekday_distribution: List[WeekdayDistributionItem]
    top_stores: List[StoreDistributionItem]
    basket_composition: List[BasketCompositionItem] = []
    tax_breakdown: Optional[List[TaxBreakdownItem]] = None
    total_tax_paid: Optional[float] = None
    favorite_day: Optional[str] = None
    top_store_name: Optional[str] = None

