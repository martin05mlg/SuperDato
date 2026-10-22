import uuid
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.analytics.schemas import (
    AnalyticsSummaryResponse,
    CategoryDistributionResponse,
    SpendingPointResponse,
    TopProductResponse,
)
from app.domains.analytics.services import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    household_id: Optional[uuid.UUID] = Query(None, description="Filtrar por ID de hogar"),
    start_date: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    """Returns aggregated KPIs: total spend, MoM variation, ticket count, average ticket, median, and last sync."""
    return await AnalyticsService.get_summary(
        db=db,
        household_id=household_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/category-distribution", response_model=List[CategoryDistributionResponse])
async def get_category_distribution(
    household_id: Optional[uuid.UUID] = Query(None, description="Filtrar por ID de hogar"),
    start_date: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    """Returns spend breakdown grouped by product category with percentage and colors."""
    return await AnalyticsService.get_category_distribution(
        db=db,
        household_id=household_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/spending-evolution", response_model=List[SpendingPointResponse])
async def get_spending_evolution(
    household_id: Optional[uuid.UUID] = Query(None, description="Filtrar por ID de hogar"),
    start_date: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    """Returns time series of daily spend for interactive charts."""
    return await AnalyticsService.get_spending_evolution(
        db=db,
        household_id=household_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/top-products", response_model=List[TopProductResponse])
async def get_top_products(
    household_id: Optional[uuid.UUID] = Query(None, description="Filtrar por ID de hogar"),
    start_date: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=50, description="Número de productos a devolver"),
    db: AsyncSession = Depends(get_db),
):
    """Returns top ranked products by accumulated spend, units and purchase count."""
    return await AnalyticsService.get_top_products(
        db=db,
        household_id=household_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
