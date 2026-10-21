import re
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.catalog.models import Category, PriceObservation, Product, ProductAlias


DEFAULT_CATEGORIES = [
    {"name": "Frutas y Verduras", "slug": "frutas-y-verduras", "icon": "apple", "color_hex": "#10B981"},
    {"name": "Carnicería y Charcutería", "slug": "carniceria-y-charcuteria", "icon": "beef", "color_hex": "#EF4444"},
    {"name": "Pescadería", "slug": "pescaderia", "icon": "fish", "color_hex": "#06B6D4"},
    {"name": "Lácteos y Huevos", "slug": "lacteos-y-huevos", "icon": "milk", "color_hex": "#F59E0B"},
    {"name": "Panadería y Pastelería", "slug": "panaderia-y-pasteleria", "icon": "croissant", "color_hex": "#D97706"},
    {"name": "Despensa y Conservas", "slug": "despensa-y-conservas", "icon": "package", "color_hex": "#6366F1"},
    {"name": "Bebidas y Refrescos", "slug": "bebidas-y-refrescos", "icon": "wine", "color_hex": "#3B82F6"},
    {"name": "Congelados", "slug": "congelados", "icon": "snowflake", "color_hex": "#8B5CF6"},
    {"name": "Limpieza y Hogar", "slug": "limpieza-y-hogar", "icon": "spray-can", "color_hex": "#14B8A6"},
    {"name": "Cuidado Personal y Perfumería", "slug": "cuidado-personal-y-perfumeria", "icon": "sparkler", "color_hex": "#EC4899"},
    {"name": "Platos Preparados", "slug": "platos-preparados", "icon": "utensils", "color_hex": "#F97316"},
    {"name": "Mascotas", "slug": "mascotas", "icon": "dog", "color_hex": "#A855F7"},
    {"name": "Otros", "slug": "otros", "icon": "shopping-bag", "color_hex": "#6B7280"},
]


class CatalogService:
    """Service handling categories, product normalization, aliases, and immutable price tracking."""

    @staticmethod
    async def ensure_system_categories(db: AsyncSession) -> Dict[str, Category]:
        """Ensures default catalog categories exist in the database and returns a mapping by slug/name."""
        query = select(Category)
        result = await db.execute(query)
        existing = {cat.slug: cat for cat in result.scalars().all()}

        created_any = False
        for cat_data in DEFAULT_CATEGORIES:
            slug = cat_data["slug"]
            if slug not in existing:
                category = Category(
                    id=uuid.uuid4(),
                    name=cat_data["name"],
                    slug=slug,
                    icon=cat_data["icon"],
                    color_hex=cat_data["color_hex"],
                    is_system=True,
                )
                db.add(category)
                existing[slug] = category
                created_any = True

        if created_any:
            await db.commit()
            for cat in existing.values():
                await db.refresh(cat)

        return existing

    @staticmethod
    def normalize_description(raw: str) -> Tuple[str, str]:
        """
        Cleans raw receipt description:
        Returns (raw_key, canonical_name)
        Example: '1 CIRUELA AMARILLA' -> ('CIRUELA AMARILLA', 'Ciruela Amarilla')
        """
        cleaned = raw.strip()
        # Remove leading standalone numbers if present (e.g. '1 CIRUELA...')
        cleaned = re.sub(r"^\d+\s+", "", cleaned).strip()
        raw_key = re.sub(r"\s+", " ", cleaned).upper()

        # Generate a human-friendly title-cased canonical name
        words = raw_key.split(" ")
        canonical_words = []
        for w in words:
            if w in ["Y", "DE", "DEL", "EN", "A", "CON", "SIN", "O"]:
                canonical_words.append(w.lower())
            elif w in ["HACENDADO", "BOSQUE", "DELIPLUS"]:
                canonical_words.append(w.capitalize())
            else:
                canonical_words.append(w.capitalize())

        canonical_name = " ".join(canonical_words)
        return raw_key, canonical_name

    @staticmethod
    async def get_or_create_product_for_line(
        db: AsyncSession,
        raw_description: str,
        category_hint: Optional[str] = None,
        unit_of_measure: str = "ud",
        weight_in_kg: Optional[float] = None,
    ) -> Product:
        """
        Normalizes a receipt line description into a Product:
        1. Checks if an alias exists for this exact text.
        2. If exists, returns the associated Product.
        3. If not, creates the canonical Product and registers the new alias.
        """
        categories = await CatalogService.ensure_system_categories(db)
        raw_key, canonical_name = CatalogService.normalize_description(raw_description)

        # 1. Search existing alias
        alias_query = (
            select(ProductAlias)
            .where(ProductAlias.raw_name_normalized == raw_key)
            .options(selectinload(ProductAlias.product).selectinload(Product.category))
        )
        alias_res = await db.execute(alias_query)
        existing_alias = alias_res.scalar_one_or_none()

        if existing_alias and existing_alias.product:
            return existing_alias.product

        # 2. Check if product already exists with canonical name
        prod_query = (
            select(Product)
            .where(Product.canonical_name == canonical_name)
            .options(selectinload(Product.category))
        )
        prod_res = await db.execute(prod_query)
        product = prod_res.scalar_one_or_none()

        if not product:
            # Map category hint to category entity
            category = None
            if category_hint:
                for cat in categories.values():
                    if cat.name.lower() == category_hint.lower() or cat.slug in category_hint.lower():
                        category = cat
                        break

            if not category:
                category = categories.get("otros") or list(categories.values())[0]

            default_unit = "kg" if weight_in_kg or unit_of_measure == "kg" else "ud"

            product = Product(
                id=uuid.uuid4(),
                canonical_name=canonical_name,
                category_id=category.id,
                default_unit=default_unit,
            )
            db.add(product)
            await db.flush()

        # 3. Create alias
        new_alias = ProductAlias(
            id=uuid.uuid4(),
            product_id=product.id,
            raw_name_normalized=raw_key,
            source="MERCADONA",
            is_verified=False,
        )
        db.add(new_alias)
        await db.commit()
        await db.refresh(product)
        return product

    @staticmethod
    async def record_price_observation(
        db: AsyncSession,
        household_id: uuid.UUID,
        product_id: uuid.UUID,
        receipt_line_id: uuid.UUID,
        observed_at: datetime,
        observed_date: date,
        unit_price: float,
        price_per_kg_or_l: Optional[float] = None,
        store_code: Optional[str] = None,
    ) -> PriceObservation:
        """
        Records an immutable price observation linking a receipt line to a product.
        If an observation already exists for this line (e.g. line edit), updates line observation.
        """
        # Ensure UTC timezone
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)

        existing_query = select(PriceObservation).where(PriceObservation.receipt_line_id == receipt_line_id)
        res = await db.execute(existing_query)
        obs = res.scalar_one_or_none()

        if obs:
            obs.product_id = product_id
            obs.unit_price = unit_price
            obs.price_per_kg_or_l = price_per_kg_or_l
            obs.store_code = store_code
        else:
            obs = PriceObservation(
                id=uuid.uuid4(),
                household_id=household_id,
                product_id=product_id,
                receipt_line_id=receipt_line_id,
                observed_at=observed_at,
                observed_date=observed_date,
                unit_price=unit_price,
                price_per_kg_or_l=price_per_kg_or_l,
                store_code=store_code,
            )
            db.add(obs)

        await db.commit()
        await db.refresh(obs)
        return obs

    @staticmethod
    async def list_categories(db: AsyncSession) -> List[Dict[str, Any]]:
        """Lists all categories with active product counts."""
        await CatalogService.ensure_system_categories(db)
        stmt = (
            select(
                Category,
                func.count(Product.id).label("product_count"),
            )
            .outerjoin(Product, Product.category_id == Category.id)
            .group_by(Category.id)
            .order_by(Category.name)
        )
        result = await db.execute(stmt)
        categories = []
        for cat, count in result.all():
            categories.append({
                "id": str(cat.id),
                "parent_id": str(cat.parent_id) if cat.parent_id else None,
                "name": cat.name,
                "slug": cat.slug,
                "icon": cat.icon,
                "color_hex": cat.color_hex,
                "is_system": cat.is_system,
                "product_count": count,
            })
        return categories

    @staticmethod
    async def list_products(
        db: AsyncSession,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Lists canonical products with latest observed prices and summary stats."""
        stmt = (
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.aliases),
                selectinload(Product.price_observations),
            )
            .order_by(Product.canonical_name)
        )

        if category_id:
            try:
                cat_uuid = uuid.UUID(category_id)
                stmt = stmt.where(Product.category_id == cat_uuid)
            except ValueError:
                pass

        if search:
            search_clean = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Product.canonical_name).like(search_clean),
                    Product.aliases.any(func.lower(ProductAlias.raw_name_normalized).like(search_clean)),
                )
            )

        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        products = result.scalars().all()

        items = []
        for p in products:
            obs_list = sorted(p.price_observations, key=lambda o: o.observed_at)
            latest_obs = obs_list[-1] if obs_list else None
            prices = [float(o.unit_price) for o in obs_list]

            items.append({
                "id": str(p.id),
                "canonical_name": p.canonical_name,
                "category_id": str(p.category_id),
                "category_name": p.category.name if p.category else "Otros",
                "category_color": p.category.color_hex if p.category else "#6B7280",
                "default_unit": p.default_unit,
                "format_description": p.format_description,
                "latest_price": float(latest_obs.unit_price) if latest_obs else None,
                "latest_price_per_kg_or_l": float(latest_obs.price_per_kg_or_l) if latest_obs and latest_obs.price_per_kg_or_l else None,
                "latest_date": str(latest_obs.observed_date) if latest_obs else None,
                "observations_count": len(obs_list),
                "min_price": min(prices) if prices else None,
                "max_price": max(prices) if prices else None,
                "aliases": [a.raw_name_normalized for a in p.aliases],
                "created_at": p.created_at.isoformat() if p.created_at else datetime.now(timezone.utc).isoformat(),
            })

        return items

    @staticmethod
    async def get_product_price_history(
        db: AsyncSession,
        product_id: uuid.UUID,
        household_id: Optional[uuid.UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        """Returns the full chronological price history observations for a product."""
        prod_query = (
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.category))
        )
        res = await db.execute(prod_query)
        product = res.scalar_one_or_none()
        if not product:
            return None

        obs_query = (
            select(PriceObservation)
            .where(PriceObservation.product_id == product_id)
            .options(selectinload(PriceObservation.receipt_line))
            .order_by(PriceObservation.observed_at.asc())
        )
        if household_id:
            obs_query = obs_query.where(PriceObservation.household_id == household_id)

        obs_res = await db.execute(obs_query)
        observations = obs_res.scalars().all()

        obs_data = []
        prices = []
        for o in observations:
            u_price = float(o.unit_price)
            prices.append(u_price)
            obs_data.append({
                "id": str(o.id),
                "household_id": str(o.household_id),
                "product_id": str(o.product_id),
                "receipt_line_id": str(o.receipt_line_id),
                "observed_at": o.observed_at.isoformat() if o.observed_at else "",
                "observed_date": str(o.observed_date),
                "unit_price": u_price,
                "price_per_kg_or_l": float(o.price_per_kg_or_l) if o.price_per_kg_or_l else None,
                "store_code": o.store_code,
                "raw_description": o.receipt_line.raw_description if o.receipt_line else None,
            })

        current_price = prices[-1] if prices else None
        min_p = min(prices) if prices else None
        max_p = max(prices) if prices else None
        change_pct = None
        if len(prices) >= 2 and prices[0] > 0:
            change_pct = round(((prices[-1] - prices[0]) / prices[0]) * 100, 2)

        return {
            "product_id": str(product.id),
            "product_name": product.canonical_name,
            "category_name": product.category.name if product.category else "Otros",
            "category_color": product.category.color_hex if product.category else "#6B7280",
            "default_unit": product.default_unit,
            "current_price": current_price,
            "min_price": min_p,
            "max_price": max_p,
            "price_change_pct": change_pct,
            "observations": obs_data,
        }

