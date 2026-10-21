from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.receipts.schemas import (
    AnalyticsSummaryResponse,
    CategoryDistributionResponse,
    SpendingPointResponse,
)
from app.domains.receipts.services import ReceiptService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    """Returns aggregated KPIs: total spend, ticket count, average ticket, median, and last sync."""
    return await ReceiptService.get_analytics_summary_from_db(db)


@router.get("/category-distribution", response_model=List[CategoryDistributionResponse])
async def get_category_distribution(db: AsyncSession = Depends(get_db)):
    """Returns spend breakdown grouped by product category."""
    return await ReceiptService.get_category_distribution_from_db(db)


@router.get("/spending-evolution", response_model=List[SpendingPointResponse])
async def get_spending_evolution(db: AsyncSession = Depends(get_db)):
    """Returns time series of daily spend for charts."""
    return await ReceiptService.get_spending_evolution_from_db(db)

