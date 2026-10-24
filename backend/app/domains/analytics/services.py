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
    "Carnicería y Charcutería": "#EF4444",
    "Pescadería": "#06B6D4",
    "Lácteos y Huevos": "#F59E0B",
    "Panadería y Pastelería": "#D97706",
    "Despensa y Conservas": "#6366F1",
    "Bebidas y Refrescos": "#3B82F6",
    "Congelados": "#8B5CF6",
    "Limpieza y Hogar": "#14B8A6",
    "Cuidado Personal y Perfumería": "#EC4899",
    "Platos Preparados": "#F97316",
    "Mascotas": "#A855F7",
    "Otros": "#6B7280",
}


class AnalyticsService:
    @staticmethod
    async def _ensure_data(db: AsyncSession):
        from app.core.config import settings
        if settings.AUTO_SEED_SAMPLES:
            count_stmt = select(func.count(Receipt.id))
            count = (await db.execute(count_stmt)).scalar_one()
            if count == 0:
                await ReceiptService.sync_sample_receipts_to_db(db)

    @staticmethod
    async def _compute_household_budget(db: AsyncSession, household_id: Optional[uuid.UUID]) -> Dict:
        """Computes household monthly budget metrics and projections."""
        monthly_budget = None
        current_month_spend = None
        budget_spent_pct = None
        budget_remaining = None
        projected_month_spend = None
        days_in_month = None
        current_day_of_month = None

        if household_id:
            from app.domains.households.models import Household
            import calendar

            hh = await db.get(Household, household_id)
            if hh and hh.settings and "monthly_budget" in hh.settings:
                try:
                    b_val = float(hh.settings["monthly_budget"])
                    if b_val > 0:
                        monthly_budget = b_val
                except (ValueError, TypeError):
                    monthly_budget = None

            today = date.today()
            first_day_of_month = date(today.year, today.month, 1)
            _, num_days = calendar.monthrange(today.year, today.month)
            days_in_month = num_days
            current_day_of_month = today.day

            cur_month_stmt = select(func.coalesce(func.sum(Receipt.total_amount), 0.0)).where(
                Receipt.household_id == household_id,
                Receipt.assignment_status == "ASSIGNED",
                Receipt.purchase_date >= first_day_of_month,
                Receipt.purchase_date <= today,
            )
            current_month_spend = round(float((await db.execute(cur_month_stmt)).scalar_one() or 0.0), 2)

            if monthly_budget:
                budget_spent_pct = round((current_month_spend / monthly_budget) * 100, 1)
                budget_remaining = round(monthly_budget - current_month_spend, 2)
                if current_day_of_month > 0:
                    daily_rate = current_month_spend / current_day_of_month
                    projected_month_spend = round(daily_rate * days_in_month, 2)

        return {
            "monthly_budget": monthly_budget,
            "current_month_spend": current_month_spend,
            "budget_spent_pct": budget_spent_pct,
            "budget_remaining": budget_remaining,
            "projected_month_spend": projected_month_spend,
            "days_in_month": days_in_month,
            "current_day_of_month": current_day_of_month,
        }

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
        query = select(Receipt).where(Receipt.assignment_status == "ASSIGNED")
        if household_id:
            query = query.where(Receipt.household_id == household_id)
        if start_date:
            query = query.where(Receipt.purchase_date >= start_date)
        if end_date:
            query = query.where(Receipt.purchase_date <= end_date)

        query = query.order_by(Receipt.purchase_datetime.desc())
        res = await db.execute(query)
        receipts = res.scalars().all()

        if not receipts:
            # Fallback if filtered range has 0 receipts - preserves household budget metrics
            budget_data = await AnalyticsService._compute_household_budget(db, household_id)
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
                "comparison_label": None,
                "max_ticket_amount": None,
                "min_ticket_amount": None,
                "shopping_frequency_days": None,
                "monthly_average_spend": None,
                **budget_data,
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

        if receipts:
            r0 = receipts[0]
            if r0.purchase_datetime:
                last_purchase_date = r0.purchase_datetime.strftime("%Y-%m-%d %H:%M:%S")
            elif r0.purchase_date and r0.purchase_time:
                last_purchase_date = f"{r0.purchase_date} {r0.purchase_time}:00" if len(r0.purchase_time) == 5 else f"{r0.purchase_date} {r0.purchase_time}"
            elif r0.purchase_date:
                last_purchase_date = r0.purchase_date.isoformat()
            else:
                last_purchase_date = None
        else:
            last_purchase_date = None

        # 2. Count total items purchased in this period
        receipt_ids = [r.id for r in receipts]
        items_stmt = select(func.coalesce(func.sum(ReceiptLine.quantity), 0)).where(
            ReceiptLine.receipt_id.in_(receipt_ids)
        )
        total_items = (await db.execute(items_stmt)).scalar_one() or 0

        # Calculate min and max ticket
        amounts = [float(r.total_amount) for r in receipts]
        max_ticket = round(max(amounts), 2) if amounts else 0.0
        min_ticket = round(min(amounts), 2) if amounts else 0.0

        # Calculate average shopping frequency in days
        shopping_frequency_days = None
        if len(receipts) >= 2:
            dates = sorted([r.purchase_date for r in receipts if r.purchase_date])
            if len(dates) >= 2:
                total_days = (dates[-1] - dates[0]).days
                if total_days > 0:
                    shopping_frequency_days = round(total_days / (len(dates) - 1), 1)

        # 3. Calculate Previous Period comparison
        prev_spend = 0.0
        period_label = "Histórico completo"
        comparison_label = None
        monthly_average_spend = None
        spend_variation = 0.0

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

            if prev_spend > 0:
                spend_variation = round(((total_spend - prev_spend) / prev_spend) * 100, 1)
                comparison_label = f"vs. periodo anterior ({prev_start.strftime('%d/%m')} - {prev_end.strftime('%d/%m')}: {prev_spend:.2f} €)"
            else:
                spend_variation = 0.0
                comparison_label = f"Sin compras en el periodo anterior ({prev_start.strftime('%d/%m')} - {prev_end.strftime('%d/%m')})"
        else:
            # When looking at all-time, estimate the monthly average across active months
            dates = sorted([r.purchase_date for r in receipts if r.purchase_date])
            if dates:
                min_d = dates[0]
                max_d = dates[-1]
                months_count = max(1, (max_d.year - min_d.year) * 12 + max_d.month - min_d.month + 1)
            else:
                months_count = 1
            monthly_avg = round(total_spend / months_count, 2)
            monthly_average_spend = monthly_avg
            prev_spend = 0.0
            spend_variation = 0.0
            comparison_label = None

        # 4. Household Monthly Budget & Projection
        budget_data = await AnalyticsService._compute_household_budget(db, household_id)

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
            "comparison_label": comparison_label,
            "max_ticket_amount": max_ticket,
            "min_ticket_amount": min_ticket,
            "shopping_frequency_days": shopping_frequency_days,
            "monthly_average_spend": monthly_average_spend,
            **budget_data,
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
            .where(Receipt.assignment_status == "ASSIGNED")
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
            .where(Receipt.assignment_status == "ASSIGNED")
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
        sort_by: str = "spend",
    ) -> List[Dict]:
        """Returns top products ranked by total spend or purchase frequency within the selected time window."""
        await AnalyticsService._ensure_data(db)
        stmt = (
            select(
                Product.id.label("prod_id"),
                func.coalesce(Product.canonical_name, ReceiptLine.raw_description).label("product_name"),
                func.coalesce(Category.name, "Otros").label("category_name"),
                func.sum(ReceiptLine.line_total).label("total_spend"),
                func.sum(ReceiptLine.quantity).label("total_quantity"),
                func.count(func.distinct(Receipt.id)).label("purchases_count"),
                Product.image_url.label("image_url"),
                Product.enriched_name.label("enriched_name"),
                Product.brand.label("brand"),
            )
            .join(Receipt, ReceiptLine.receipt_id == Receipt.id)
            .join(Product, ReceiptLine.product_id == Product.id, isouter=True)
            .join(Category, Product.category_id == Category.id, isouter=True)
            .where(Receipt.assignment_status == "ASSIGNED")
        )

        if household_id:
            stmt = stmt.where(Receipt.household_id == household_id)
        if start_date:
            stmt = stmt.where(Receipt.purchase_date >= start_date)
        if end_date:
            stmt = stmt.where(Receipt.purchase_date <= end_date)

        group_stmt = stmt.group_by("prod_id", "product_name", "category_name", Product.image_url, Product.enriched_name, Product.brand)

        if sort_by == "purchases":
            ordered_stmt = group_stmt.order_by(desc("purchases_count"), desc("total_quantity"), desc("total_spend")).limit(limit)
        elif sort_by == "quantity":
            ordered_stmt = group_stmt.order_by(desc("total_quantity"), desc("total_spend")).limit(limit)
        else:
            ordered_stmt = group_stmt.order_by(desc("total_spend"), desc("purchases_count")).limit(limit)

        res = await db.execute(ordered_stmt)
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
                "image_url": r[6] if len(r) > 6 else None,
                "enriched_name": r[7] if len(r) > 7 else None,
                "brand": r[8] if len(r) > 8 else None,
            })

        return result

    @staticmethod
    async def get_habits(
        db: AsyncSession,
        household_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict:
        """
        Calculates household shopping habits and telemetry:
        1. Weekday distribution (e.g. favorite day to shop).
        2. Top stores visited with visit counts and spend.
        3. Detailed tax breakdown (IVA 4%, 10%, 21%).
        """
        from collections import defaultdict
        from app.domains.receipts.models import ReceiptTaxLine

        await AnalyticsService._ensure_data(db)

        # 1. Fetch matching receipts
        query = select(Receipt).where(Receipt.assignment_status == "ASSIGNED")
        if household_id:
            query = query.where(Receipt.household_id == household_id)
        if start_date:
            query = query.where(Receipt.purchase_date >= start_date)
        if end_date:
            query = query.where(Receipt.purchase_date <= end_date)

        res = await db.execute(query)
        receipts = res.scalars().all()

        if not receipts:
            return {
                "weekday_distribution": [],
                "top_stores": [],
                "basket_composition": [],
                "tax_breakdown": [],
                "total_tax_paid": 0.0,
                "favorite_day": None,
                "top_store_name": None,
            }

        total_spend = sum(float(r.total_amount) for r in receipts) or 1.0

        # Weekdays
        day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        by_day = defaultdict(lambda: {"count": 0, "spend": 0.0})
        for r in receipts:
            if r.purchase_date:
                wd = r.purchase_date.weekday()
                by_day[wd]["count"] += 1
                by_day[wd]["spend"] += float(r.total_amount)

        weekday_dist = []
        for wd in range(7):
            d = by_day[wd]
            weekday_dist.append({
                "day_name": day_names[wd],
                "day_number": wd,
                "receipt_count": d["count"],
                "total_spend": round(d["spend"], 2),
                "percentage": round((d["spend"] / total_spend) * 100, 1) if total_spend > 0 else 0.0,
            })

        active_days = [w for w in weekday_dist if w["receipt_count"] > 0]
        favorite_day = max(active_days, key=lambda x: x["total_spend"])["day_name"] if active_days else None

        # Top Stores
        by_store = defaultdict(lambda: {"city": "", "count": 0, "spend": 0.0})
        for r in receipts:
            raw_addr = (r.store_address or "Mercadona").strip()
            city = (r.store_city or "").strip()
            cleaned_addr = raw_addr
            if "VENANCIO HUARTE" in raw_addr.upper():
                cleaned_addr = "C/ Padre Venancio Huarte"
                city = "Zaragoza"
            by_store[(cleaned_addr, city)]["count"] += 1
            by_store[(cleaned_addr, city)]["spend"] += float(r.total_amount)

        top_stores = []
        sorted_stores = sorted(by_store.items(), key=lambda item: item[1]["count"], reverse=True)
        for (addr, city), data in sorted_stores[:5]:
            top_stores.append({
                "store_name": addr,
                "city": city or None,
                "receipt_count": data["count"],
                "total_spend": round(data["spend"], 2),
                "percentage": round((data["spend"] / total_spend) * 100, 1),
            })
        top_store_name = top_stores[0]["store_name"] if top_stores else None

        receipt_ids = [r.id for r in receipts]

        # Basket Macro Composition for Household
        lines_stmt = (
            select(
                func.coalesce(Category.slug, "otros").label("slug"),
                func.sum(ReceiptLine.line_total).label("total_spend"),
                func.count(ReceiptLine.id).label("items_count"),
            )
            .join(Receipt, ReceiptLine.receipt_id == Receipt.id)
            .outerjoin(Product, ReceiptLine.product_id == Product.id)
            .outerjoin(Category, Product.category_id == Category.id)
            .where(Receipt.id.in_(receipt_ids))
            .group_by(Category.slug)
        )
        l_res = await db.execute(lines_stmt)
        cat_data = {row.slug: {"spend": float(row.total_spend or 0.0), "count": int(row.items_count or 0)} for row in l_res}

        macro_groups_def = [
            {
                "group_name": "Productos Frescos",
                "description": "Frutas, verduras, carne y pescado fresco",
                "icon": "Apple",
                "color_hex": "#10B981",
                "slugs": ["frutas-y-verduras", "carniceria-y-charcuteria", "pescaderia"],
            },
            {
                "group_name": "Despensa y Básicos",
                "description": "Lácteos, panadería, conservas, bebidas y legumbres",
                "icon": "Package",
                "color_hex": "#3B82F6",
                "slugs": ["lacteos-y-huevos", "panaderia-y-pasteleria", "despensa-y-conservas", "bebidas-y-refrescos", "congelados"],
            },
            {
                "group_name": "Hogar y Cuidado Personal",
                "description": "Droguería, limpieza, higiene y mascotas",
                "icon": "Sparkles",
                "color_hex": "#14B8A6",
                "slugs": ["limpieza-y-hogar", "cuidado-personal-y-perfumeria", "mascotas"],
            },
            {
                "group_name": "Platos Preparados y Varios",
                "description": "Listos para comer y miscelánea",
                "icon": "UtensilsCrossed",
                "color_hex": "#F97316",
                "slugs": ["platos-preparados", "otros"],
            },
        ]

        total_lines_spend = sum(d["spend"] for d in cat_data.values()) or total_spend
        basket_composition = []
        for g in macro_groups_def:
            g_spend = sum(cat_data.get(s, {}).get("spend", 0.0) for s in g["slugs"])
            g_count = sum(cat_data.get(s, {}).get("count", 0) for s in g["slugs"])
            pct = round((g_spend / total_lines_spend) * 100, 1) if total_lines_spend > 0 else 0.0
            basket_composition.append({
                "group_name": g["group_name"],
                "description": g["description"],
                "icon": g["icon"],
                "color_hex": g["color_hex"],
                "total_spend": round(g_spend, 2),
                "percentage": pct,
                "items_count": g_count,
            })

        # Tax Breakdown
        tax_stmt = select(ReceiptTaxLine).where(ReceiptTaxLine.receipt_id.in_(receipt_ids))
        t_res = await db.execute(tax_stmt)
        tax_lines = t_res.scalars().all()

        by_rate = defaultdict(lambda: {"base": 0.0, "tax": 0.0, "total": 0.0})
        for t in tax_lines:
            rate = float(t.tax_rate_percent)
            if rate in [4.0, 10.0, 21.0, 0.0, 2.0, 5.0]:
                by_rate[rate]["base"] += float(t.taxable_base)
                by_rate[rate]["tax"] += float(t.tax_amount)
                by_rate[rate]["total"] += float(t.total_with_tax)

        total_tax_paid = sum(v["tax"] for v in by_rate.values())
        tax_breakdown = []
        for rate, vals in sorted(by_rate.items(), key=lambda x: x[0]):
            pct_of_tax = round((vals["tax"] / total_tax_paid) * 100, 1) if total_tax_paid > 0 else 0.0
            tax_breakdown.append({
                "tax_rate_percent": rate,
                "taxable_base": round(vals["base"], 2),
                "tax_amount": round(vals["tax"], 2),
                "total_with_tax": round(vals["total"], 2),
                "percentage_of_tax": pct_of_tax,
            })

        # Calculate Brand Share (Marcas Propias de Mercadona vs Fabricante)
        all_lines_stmt = (
            select(
                ReceiptLine.line_total,
                ReceiptLine.raw_description,
                Product.brand,
                Product.canonical_name,
            )
            .join(Receipt, ReceiptLine.receipt_id == Receipt.id)
            .outerjoin(Product, ReceiptLine.product_id == Product.id)
            .where(Receipt.id.in_(receipt_ids))
        )
        all_l_res = await db.execute(all_lines_stmt)
        lines_data = all_l_res.all()

        own_brands_keywords = ["HACENDADO", "BOSQUE VERDE", "DELIPLUS", "COMPY", "MAY"]
        own_brand_spend = 0.0
        own_brand_count = 0
        external_brand_spend = 0.0
        external_brand_count = 0

        for row in lines_data:
            lt = float(row.line_total or 0.0)
            brand_str = (row.brand or "").upper()
            raw_desc = (row.raw_description or "").upper()
            canon_desc = (row.canonical_name or "").upper()

            is_own = any(k in brand_str or k in raw_desc or k in canon_desc for k in own_brands_keywords)
            if is_own:
                own_brand_spend += lt
                own_brand_count += 1
            else:
                external_brand_spend += lt
                external_brand_count += 1

        total_brand_spend = (own_brand_spend + external_brand_spend) or 1.0
        own_pct = round((own_brand_spend / total_brand_spend) * 100, 1)
        ext_pct = round((external_brand_spend / total_brand_spend) * 100, 1)

        brand_share = [
            {
                "brand_type": "MARCAS_PROPIAS",
                "label": "Marcas Propias (Hacendado, Bosque Verde, Deliplus)",
                "total_spend": round(own_brand_spend, 2),
                "percentage": own_pct,
                "items_count": own_brand_count,
                "color_hex": "#10B981",
            },
            {
                "brand_type": "MARCAS_FABRICANTE",
                "label": "Marcas de Fabricante",
                "total_spend": round(external_brand_spend, 2),
                "percentage": ext_pct,
                "items_count": external_brand_count,
                "color_hex": "#6366F1",
            },
        ]

        return {
            "weekday_distribution": weekday_dist,
            "top_stores": top_stores,
            "basket_composition": basket_composition,
            "brand_share": brand_share,
            "own_brands_percentage": own_pct,
            "tax_breakdown": tax_breakdown,
            "total_tax_paid": round(total_tax_paid, 2),
            "favorite_day": favorite_day,
            "top_store_name": top_store_name,
        }
