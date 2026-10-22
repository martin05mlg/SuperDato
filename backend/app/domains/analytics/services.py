import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.catalog.models import Category, Product
from app.domains.receipts.models import Receipt, ReceiptLine
from app.domains.receipts.services import ReceiptService

CATEGORY_COLORS = {
    "Frutas y Verduras": "#10B981",
    "Carnicería y Aves": "#EF4444",
    "Pescadería": "#06B6D4",
    "Lácteos y Quesos": "#F59E0B",
    "Platos Preparados": "#8B5CF6",
    "Bebidas": "#3B82F6",
    "Cuidado Personal": "#EC4899",
    "Aperitivos y Snacks": "#F97316",
    "Alimentación General": "#6B7280",
    "Limpieza y Hogar": "#14B8A6",
    "Panadería y Pastelería": "#D97706",
    "Congelados": "#38BDF8",
    "Mascotas": "#A855F7",
    "Servicios": "#94A3B8",
    "Otros": "#64748B",
}


class AnalyticsService:
    @staticmethod
    async def _ensure_data(db: AsyncSession):
        count_stmt = select(func.count(Receipt.id))
        count = (await db.execute(count_stmt)).scalar_one()
        if count == 0:
            await ReceiptService.sync_sample_receipts_to_db(db)

    @staticmethod
    async def get_summary(
        db: AsyncSession,
        household_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict:
        """
        Calculates aggregated KPIs:
        total spend, MoM/period comparison, receipt count, average ticket, median,
        total item count, and latest purchase date.
        """
        await AnalyticsService._ensure_data(db)

        # 1. Base query for current period
        query = select(Receipt)
        if household_id:
            query = query.where(Receipt.household_id == household_id)
        if start_date:
            query = query.where(Receipt.purchase_date >= start_date)
        if end_date:
            query = query.where(Receipt.purchase_date <= end_date)

        query = query.order_by(Receipt.purchase_date.desc())
        res = await db.execute(query)
        receipts = res.scalars().all()

        if not receipts:
            # Fallback if filtered range has 0 receipts
            return {
                "total_spend": 0.0,
                "previous_spend": 0.0,
                "spend_variation_pct": 0.0,
                "receipt_count": 0,
                "average_ticket": 0.0,
                "median_ticket": 0.0,
                "total_items_count": 0,
                "last_purchase_date": None,
                "last_sync_at": "Al día",
                "period_label": "Sin datos en el rango seleccionado",
            }

        total_spend = sum(float(r.total_amount) for r in receipts)
        count = len(receipts)
        avg_ticket = round(total_spend / count, 2) if count > 0 else 0.0

        # Calculate median ticket
        amounts = sorted(float(r.total_amount) for r in receipts)
        if count % 2 == 1:
            median_ticket = amounts[count // 2]
        else:
            median_ticket = round((amounts[count // 2 - 1] + amounts[count // 2]) / 2, 2)

        last_purchase_date = receipts[0].purchase_date.isoformat() if receipts else None

        # 2. Count total items purchased in this period
        receipt_ids = [r.id for r in receipts]
        items_stmt = select(func.coalesce(func.sum(ReceiptLine.quantity), 0)).where(
            ReceiptLine.receipt_id.in_(receipt_ids)
        )
        total_items = (await db.execute(items_stmt)).scalar_one() or 0

        # 3. Calculate Previous Period spend for MoM comparison
        prev_spend = 0.0
        period_label = "Histórico completo"

        if start_date and end_date:
            duration_days = (end_date - start_date).days + 1
            prev_end = start_date - timedelta(days=1)
            prev_start = prev_end - timedelta(days=duration_days - 1)
            period_label = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"

            prev_stmt = select(func.coalesce(func.sum(Receipt.total_amount), 0.0)).where(
                Receipt.purchase_date >= prev_start,
                Receipt.purchase_date <= prev_end,
            )
            if household_id:
                prev_stmt = prev_stmt.where(Receipt.household_id == household_id)
            prev_spend = float((await db.execute(prev_stmt)).scalar_one() or 0.0)
        else:
            # When looking at all-time, compare the current calendar month with the previous month
            today = date.today()
            curr_month_start = today.replace(day=1)
            prev_month_end = curr_month_start - timedelta(days=1)
            prev_month_start = prev_month_end.replace(day=1)

            curr_month_stmt = select(func.coalesce(func.sum(Receipt.total_amount), 0.0)).where(
                Receipt.purchase_date >= curr_month_start,
                Receipt.purchase_date <= today,
            )
            prev_month_stmt = select(func.coalesce(func.sum(Receipt.total_amount), 0.0)).where(
                Receipt.purchase_date >= prev_month_start,
                Receipt.purchase_date <= prev_month_end,
            )
            if household_id:
                curr_month_stmt = curr_month_stmt.where(Receipt.household_id == household_id)
                prev_month_stmt = prev_month_stmt.where(Receipt.household_id == household_id)

            curr_m_spend = float((await db.execute(curr_month_stmt)).scalar_one() or 0.0)
            prev_m_spend = float((await db.execute(prev_month_stmt)).scalar_one() or 0.0)

            prev_spend = prev_m_spend
            if prev_spend > 0:
                spend_variation = round(((curr_m_spend - prev_spend) / prev_spend) * 100, 1)
            else:
                spend_variation = 0.0

            return {
                "total_spend": round(total_spend, 2),
                "previous_spend": round(prev_spend, 2),
                "spend_variation_pct": spend_variation,
                "receipt_count": count,
                "average_ticket": avg_ticket,
                "median_ticket": median_ticket,
                "total_items_count": int(total_items),
                "last_purchase_date": last_purchase_date,
                "last_sync_at": "Sincronizado vía Gmail / PDF",
                "period_label": period_label,
            }

        spend_variation = 0.0
        if prev_spend > 0:
            spend_variation = round(((total_spend - prev_spend) / prev_spend) * 100, 1)

        return {
            "total_spend": round(total_spend, 2),
            "previous_spend": round(prev_spend, 2),
            "spend_variation_pct": spend_variation,
            "receipt_count": count,
            "average_ticket": avg_ticket,
            "median_ticket": median_ticket,
            "total_items_count": int(total_items),
            "last_purchase_date": last_purchase_date,
            "last_sync_at": "Sincronizado vía Gmail / PDF",
            "period_label": period_label,
        }

    @staticmethod
    async def get_category_distribution(
        db: AsyncSession,
        household_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict]:
        """Calculates spend grouped by product category for the given filter parameters."""
        await AnalyticsService._ensure_data(db)

        stmt = (
            select(
                func.coalesce(Category.name, "Otros").label("cat_name"),
                func.sum(ReceiptLine.line_total).label("total_spend"),
                func.count(ReceiptLine.id).label("items_count"),
            )
            .join(Receipt, ReceiptLine.receipt_id == Receipt.id)
            .join(Product, ReceiptLine.product_id == Product.id, isouter=True)
            .join(Category, Product.category_id == Category.id, isouter=True)
        )

        if household_id:
            stmt = stmt.where(Receipt.household_id == household_id)
        if start_date:
            stmt = stmt.where(Receipt.purchase_date >= start_date)
        if end_date:
            stmt = stmt.where(Receipt.purchase_date <= end_date)

        stmt = stmt.group_by("cat_name").order_by(desc("total_spend"))
        res = await db.execute(stmt)
        rows = res.all()

        if not rows and not start_date and not end_date and not household_id:
            return ReceiptService.get_category_distribution()

        total_all = sum(float(r[1]) for r in rows) or 1.0

        distribution = []
        for cat_name, spend, items_count in rows:
            amount = float(spend)
            pct = round((amount / total_all) * 100, 1)
            distribution.append({
                "category_name": cat_name,
                "color_hex": CATEGORY_COLORS.get(cat_name, "#64748B"),
                "total_spend": round(amount, 2),
                "percentage": pct,
                "items_count": int(items_count),
            })

        return distribution

    @staticmethod
    async def get_spending_evolution(
        db: AsyncSession,
        household_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict]:
        """Calculates daily spend time series for the given period."""
        await AnalyticsService._ensure_data(db)

        stmt = (
            select(
                Receipt.purchase_date,
                func.sum(Receipt.total_amount).label("total_amount"),
                func.count(Receipt.id).label("receipt_count"),
            )
        )

        if household_id:
            stmt = stmt.where(Receipt.household_id == household_id)
        if start_date:
            stmt = stmt.where(Receipt.purchase_date >= start_date)
        if end_date:
            stmt = stmt.where(Receipt.purchase_date <= end_date)

        stmt = stmt.group_by(Receipt.purchase_date).order_by(Receipt.purchase_date.asc())
        res = await db.execute(stmt)
        rows = res.all()

        if not rows and not start_date and not end_date and not household_id:
            return ReceiptService.get_spending_evolution()

        return [
            {
                "date": r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0]),
                "total_amount": round(float(r[1]), 2),
                "receipt_count": int(r[2]),
            }
            for r in rows
        ]

    @staticmethod
    async def get_top_products(
        db: AsyncSession,
        household_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Returns the top products ranked by total spend within the selected time window."""
        await AnalyticsService._ensure_data(db)
        stmt = (
            select(
                Product.id.label("prod_id"),
                func.coalesce(Product.canonical_name, ReceiptLine.raw_description).label("product_name"),
                func.coalesce(Category.name, "Otros").label("category_name"),
                func.sum(ReceiptLine.line_total).label("total_spend"),
                func.sum(ReceiptLine.quantity).label("total_quantity"),
                func.count(func.distinct(Receipt.id)).label("purchases_count"),
            )
            .join(Receipt, ReceiptLine.receipt_id == Receipt.id)
            .join(Product, ReceiptLine.product_id == Product.id, isouter=True)
            .join(Category, Product.category_id == Category.id, isouter=True)
        )

        if household_id:
            stmt = stmt.where(Receipt.household_id == household_id)
        if start_date:
            stmt = stmt.where(Receipt.purchase_date >= start_date)
        if end_date:
            stmt = stmt.where(Receipt.purchase_date <= end_date)

        stmt = (
            stmt.group_by("prod_id", "product_name", "category_name")
            .order_by(desc("total_spend"))
            .limit(limit)
        )

        res = await db.execute(stmt)
        rows = res.all()

        result = []
        for r in rows:
            prod_id = str(r[0]) if r[0] else None
            p_name = r[1]
            cat_name = r[2]
            spend = float(r[3])
            qty = float(r[4])
            p_count = int(r[5])
            avg_p = round(spend / qty, 2) if qty > 0 else 0.0

            result.append({
                "product_id": prod_id,
                "product_name": p_name,
                "category_name": cat_name,
                "total_spend": round(spend, 2),
                "total_quantity": round(qty, 2),
                "purchases_count": p_count,
                "average_price": avg_p,
            })

        return result
