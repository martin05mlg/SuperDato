from typing import List
from fastapi import APIRouter
from app.domains.receipts.schemas import (
    AnalyticsSummaryResponse,
    CategoryDistributionResponse,
    SpendingPointResponse,
)
from app.domains.receipts.services import ReceiptService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary():
    """Returns aggregated KPIs: total spend, ticket count, average ticket, median, and last sync."""
    return ReceiptService.get_analytics_summary()


@router.get("/category-distribution", response_model=List[CategoryDistributionResponse])
async def get_category_distribution():
    """Returns spend breakdown grouped by product category."""
    return ReceiptService.get_category_distribution()


@router.get("/spending-evolution", response_model=List[SpendingPointResponse])
async def get_spending_evolution():
    """Returns time series of daily spend for charts."""
    return ReceiptService.get_spending_evolution()

