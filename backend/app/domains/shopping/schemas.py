import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ShoppingItemCreate(BaseModel):
    household_id: uuid.UUID
    name: str
    product_id: Optional[uuid.UUID] = None
    quantity: float = 1.0
    unit_of_measure: str = "ud"
    estimated_unit_price: Optional[float] = None
    notes: Optional[str] = None


class ShoppingItemUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = None
    unit_of_measure: Optional[str] = None
    estimated_unit_price: Optional[float] = None
    is_checked: Optional[bool] = None
    notes: Optional[str] = None


class ShoppingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    product_id: Optional[uuid.UUID] = None
    name: str
    quantity: float
    unit_of_measure: str
    estimated_unit_price: Optional[float] = None
    estimated_total: float
    is_checked: bool
    checked_at: Optional[datetime] = None
    notes: Optional[str] = None
    category_name: str = "Otros"
    category_color: str = "#6B7280"
    image_url: Optional[str] = None
    brand: Optional[str] = None
    created_at: datetime


class ShoppingListSummaryResponse(BaseModel):
    items: List[ShoppingItemResponse]
    total_count: int
    checked_count: int
    pending_count: int
    estimated_total_cost: float
    estimated_checked_cost: float
    estimated_pending_cost: float


class ShoppingSuggestionItem(BaseModel):
    product_id: uuid.UUID
    name: str
    category_name: str
    category_color: str
    image_url: Optional[str] = None
    brand: Optional[str] = None
    latest_price: Optional[float] = None
    unit_of_measure: str
    avg_frequency_days: float
    days_since_last_purchase: int
    purchases_count: int
    reason: str

