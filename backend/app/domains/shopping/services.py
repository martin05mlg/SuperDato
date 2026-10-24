import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.catalog.models import Category, PriceObservation, Product
from app.domains.catalog.services import CatalogService
from app.domains.shopping.models import ShoppingListItem
from app.domains.shopping.schemas import (
    ShoppingItemCreate,
    ShoppingItemResponse,
    ShoppingItemUpdate,
    ShoppingListSummaryResponse,
    ShoppingSuggestionItem,
)


class ShoppingService:
    @staticmethod
    async def get_shopping_list(
        db: AsyncSession,
        household_id: uuid.UUID,
    ) -> ShoppingListSummaryResponse:
        """Returns active shopping list items with product metadata and cost estimates."""
        stmt = (
            select(ShoppingListItem)
            .where(ShoppingListItem.household_id == household_id)
            .options(
                selectinload(ShoppingListItem.product).selectinload(Product.category),
                selectinload(ShoppingListItem.product).selectinload(Product.price_observations),
            )
            .order_by(ShoppingListItem.is_checked.asc(), ShoppingListItem.created_at.asc())
        )
        res = await db.execute(stmt)
        db_items = res.scalars().all()

        items: List[ShoppingItemResponse] = []
        total_cost = 0.0
        checked_cost = 0.0
        pending_cost = 0.0
        checked_count = 0

        for item in db_items:
            cat_name = "Otros"
            cat_color = "#6B7280"
            img_url = None
            brand_name = None
            est_unit_price = float(item.estimated_unit_price) if item.estimated_unit_price is not None else None

            if item.product:
                if item.product.category:
                    cat_name = item.product.category.name
                    cat_color = item.product.category.color_hex or "#6B7280"
                img_url = item.product.image_url
                brand_name = item.product.brand
                if est_unit_price is None and item.product.price_observations:
                    sorted_obs = sorted(item.product.price_observations, key=lambda o: o.observed_at)
                    if sorted_obs:
                        est_unit_price = float(sorted_obs[-1].unit_price)

            qty = float(item.quantity)
            est_total = round(qty * (est_unit_price or 0.0), 2)

            total_cost += est_total
            if item.is_checked:
                checked_cost += est_total
                checked_count += 1
            else:
                pending_cost += est_total

            items.append(
                ShoppingItemResponse(
                    id=item.id,
                    household_id=item.household_id,
                    product_id=item.product_id,
                    name=item.name,
                    quantity=qty,
                    unit_of_measure=item.unit_of_measure,
                    estimated_unit_price=est_unit_price,
                    estimated_total=est_total,
                    is_checked=item.is_checked,
                    checked_at=item.checked_at,
                    notes=item.notes,
                    category_name=cat_name,
                    category_color=cat_color,
                    image_url=img_url,
                    brand=brand_name,
                    created_at=item.created_at,
                )
            )

        return ShoppingListSummaryResponse(
            items=items,
            total_count=len(items),
            checked_count=checked_count,
            pending_count=len(items) - checked_count,
            estimated_total_cost=round(total_cost, 2),
            estimated_checked_cost=round(checked_cost, 2),
            estimated_pending_cost=round(pending_cost, 2),
        )

    @staticmethod
    async def add_item(
        db: AsyncSession,
        data: ShoppingItemCreate,
        user_id: uuid.UUID,
    ) -> ShoppingItemResponse:
        """Adds a new item to the household shopping list, linking catalog metadata."""
        product = None
        est_price = data.estimated_unit_price

        if data.product_id:
            product = await db.get(Product, data.product_id)
        elif data.name.strip():
            # Try to resolve product by name
            product = await CatalogService.get_or_create_product_for_line(
                db=db,
                raw_description=data.name.strip(),
                unit_of_measure=data.unit_of_measure,
            )

        if product:
            if est_price is None:
                # Fetch latest price observation for this product
                obs_stmt = (
                    select(PriceObservation)
                    .where(PriceObservation.product_id == product.id)
                    .order_by(PriceObservation.observed_at.desc())
                    .limit(1)
                )
                obs_res = await db.execute(obs_stmt)
                last_obs = obs_res.scalar_one_or_none()
                if last_obs:
                    est_price = float(last_obs.unit_price)

        item = ShoppingListItem(
            id=uuid.uuid4(),
            household_id=data.household_id,
            product_id=product.id if product else None,
            name=product.canonical_name if product else data.name.strip(),
            quantity=data.quantity,
            unit_of_measure=data.unit_of_measure,
            estimated_unit_price=est_price,
            is_checked=False,
            notes=data.notes,
            created_by_user_id=user_id,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)

        # Reload with relationships
        full_summary = await ShoppingService.get_shopping_list(db, data.household_id)
        for resp_item in full_summary.items:
            if resp_item.id == item.id:
                return resp_item

        return ShoppingItemResponse(
            id=item.id,
            household_id=item.household_id,
            product_id=item.product_id,
            name=item.name,
            quantity=float(item.quantity),
            unit_of_measure=item.unit_of_measure,
            estimated_unit_price=float(item.estimated_unit_price) if item.estimated_unit_price else None,
            estimated_total=round(float(item.quantity) * (float(item.estimated_unit_price or 0.0)), 2),
            is_checked=item.is_checked,
            checked_at=item.checked_at,
            notes=item.notes,
            category_name="Otros",
            category_color="#6B7280",
            image_url=None,
            brand=None,
            created_at=item.created_at,
        )

    @staticmethod
    async def update_item(
        db: AsyncSession,
        item_id: uuid.UUID,
        household_id: uuid.UUID,
        data: ShoppingItemUpdate,
    ) -> ShoppingItemResponse:
        """Updates item attributes (checked state, quantity, notes)."""
        item = await db.get(ShoppingListItem, item_id)
        if not item or item.household_id != household_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado")

        if data.name is not None:
            item.name = data.name.strip()
        if data.quantity is not None:
            item.quantity = max(0.001, data.quantity)
        if data.unit_of_measure is not None:
            item.unit_of_measure = data.unit_of_measure
        if data.estimated_unit_price is not None:
            item.estimated_unit_price = data.estimated_unit_price
        if data.notes is not None:
            item.notes = data.notes
        if data.is_checked is not None:
            item.is_checked = data.is_checked
            item.checked_at = datetime.now(timezone.utc) if data.is_checked else None

        await db.commit()
        await db.refresh(item)

        summary = await ShoppingService.get_shopping_list(db, household_id)
        for resp_item in summary.items:
            if resp_item.id == item.id:
                return resp_item

        return ShoppingItemResponse(
            id=item.id,
            household_id=item.household_id,
            product_id=item.product_id,
            name=item.name,
            quantity=float(item.quantity),
            unit_of_measure=item.unit_of_measure,
            estimated_unit_price=float(item.estimated_unit_price) if item.estimated_unit_price else None,
            estimated_total=round(float(item.quantity) * (float(item.estimated_unit_price or 0.0)), 2),
            is_checked=item.is_checked,
            checked_at=item.checked_at,
            notes=item.notes,
            created_at=item.created_at,
        )

    @staticmethod
    async def delete_item(
        db: AsyncSession,
        item_id: uuid.UUID,
        household_id: uuid.UUID,
    ) -> None:
        """Deletes a single item from the shopping list."""
        item = await db.get(ShoppingListItem, item_id)
        if not item or item.household_id != household_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado")
        await db.delete(item)
        await db.commit()

    @staticmethod
    async def clear_checked(
        db: AsyncSession,
        household_id: uuid.UUID,
    ) -> int:
        """Removes all checked items from the shopping list."""
        stmt = delete(ShoppingListItem).where(
            ShoppingListItem.household_id == household_id,
            ShoppingListItem.is_checked == True,
        )
        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount

    @staticmethod
    async def get_replenishment_suggestions(
        db: AsyncSession,
        household_id: uuid.UUID,
    ) -> List[ShoppingSuggestionItem]:
        """
        Analyzes historical purchase cycles to identify products likely needing replenishment.
        Formula: average_days_between_purchases vs days_elapsed_since_last_purchase.
        """
        # 1. Fetch products currently on the shopping list to exclude them
        cur_stmt = select(ShoppingListItem.product_id).where(
            ShoppingListItem.household_id == household_id,
            ShoppingListItem.is_checked == False,
            ShoppingListItem.product_id.isnot(None),
        )
        existing_res = await db.execute(cur_stmt)
        existing_pids = set(existing_res.scalars().all())

        # 2. Fetch all price observations for this household
        obs_stmt = (
            select(PriceObservation)
            .where(PriceObservation.household_id == household_id)
            .options(
                selectinload(PriceObservation.product).selectinload(Product.category)
            )
            .order_by(PriceObservation.observed_date.asc())
        )
        obs_res = await db.execute(obs_stmt)
        observations = obs_res.scalars().all()

        # Group by product
        from collections import defaultdict
        product_dates = defaultdict(list)
        product_map = {}
        product_prices = {}

        for obs in observations:
            if not obs.product:
                continue
            pid = obs.product.id
            if pid in existing_pids:
                continue
            product_dates[pid].append(obs.observed_date)
            product_map[pid] = obs.product
            product_prices[pid] = float(obs.unit_price)

        today = date.today()
        suggestions: List[ShoppingSuggestionItem] = []

        for pid, dates in product_dates.items():
            # Only consider products bought at least 2 times
            if len(dates) < 2:
                continue

            unique_dates = sorted(list(set(dates)))
            if len(unique_dates) < 2:
                continue

            first_date = unique_dates[0]
            last_date = unique_dates[-1]
            total_days = (last_date - first_date).days
            avg_frequency = round(total_days / (len(unique_dates) - 1), 1)

            # Avoid noise with too infrequent or same-day purchases
            if avg_frequency < 2.0:
                continue

            days_since = (today - last_date).days

            # Trigger suggestion if we are at or past 85% of average cycle
            if days_since >= avg_frequency * 0.85:
                prod = product_map[pid]
                urgency = round(days_since / avg_frequency, 2)
                reason = (
                    f"Sueles comprarlo cada ~{avg_frequency:.0f} días (hace {days_since} días de tu última compra)"
                )

                cat_name = prod.category.name if prod.category else "Otros"
                cat_color = prod.category.color_hex if prod.category else "#6B7280"

                suggestions.append(
                    ShoppingSuggestionItem(
                        product_id=prod.id,
                        name=prod.canonical_name,
                        category_name=cat_name,
                        category_color=cat_color,
                        image_url=prod.image_url,
                        brand=prod.brand,
                        latest_price=product_prices.get(pid),
                        unit_of_measure=prod.default_unit or "ud",
                        avg_frequency_days=avg_frequency,
                        days_since_last_purchase=days_since,
                        purchases_count=len(dates),
                        reason=reason,
                    )
                )

        # Sort suggestions by relative urgency
        suggestions.sort(key=lambda s: s.days_since_last_purchase / s.avg_frequency_days, reverse=True)
        return suggestions[:12]

