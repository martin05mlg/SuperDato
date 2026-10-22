import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.domains.auth.models import User
from app.domains.households.models import HouseholdMembership
from app.domains.households.permissions import get_current_user
from app.domains.catalog.matcher import MercadonaMatcherService, normalize_string
from app.domains.catalog.mercadona_client import MercadonaStorefrontClient
from app.domains.catalog.models import Category, MercadonaOnlineProduct, Product, ProductAlias
from app.domains.catalog.schemas import (
    CategoryResponse,
    MercadonaCandidateItem,
    MercadonaConfirmMatchRequest,
    MercadonaEnrichRequest,
    MercadonaEnrichResponse,
    MercadonaOnlineProductResponse,
    MercadonaRejectMatchRequest,
    MercadonaSuggestionItem,
    MercadonaSyncRequest,
    MercadonaSyncResponse,
    PriceHistoryResponse,
    ProductAliasCreate,
    ProductAliasResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.domains.catalog.services import CatalogService

router = APIRouter(prefix="/catalog", tags=["Catálogo y Precios"])


async def verify_household_access(
    household_id: Optional[uuid.UUID],
    current_user: User,
    db: AsyncSession,
) -> None:
    """Verifies that the current user belongs to the target household."""
    if household_id and not current_user.is_superuser:
        res = await db.execute(
            select(HouseholdMembership).where(
                HouseholdMembership.household_id == household_id,
                HouseholdMembership.user_id == current_user.id,
            )
        )
        if not res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado: No perteneces a este hogar.",
            )


def format_product_dict(prod: Product, obs_list=None, category=None, aliases=None) -> dict:
    if obs_list is None:
        obs_list = list(prod.price_observations) if "price_observations" in prod.__dict__ else []
    obs_list = sorted(obs_list, key=lambda o: o.observed_at)
    latest_obs = obs_list[-1] if obs_list else None
    prices = [float(o.unit_price) for o in obs_list]

    cat = category
    if cat is None and "category" in prod.__dict__:
        cat = prod.category

    if aliases is None:
        alias_names = [a.raw_name_normalized for a in prod.aliases] if "aliases" in prod.__dict__ else []
    else:
        alias_names = aliases

    return {
        "id": str(prod.id),
        "canonical_name": prod.canonical_name,
        "category_id": str(prod.category_id),
        "category_name": cat.name if cat else "Otros",
        "category_color": cat.color_hex if cat else "#6B7280",
        "default_unit": prod.default_unit,
        "format_description": prod.format_description,
        "latest_price": float(latest_obs.unit_price) if latest_obs else None,
        "latest_price_per_kg_or_l": float(latest_obs.price_per_kg_or_l) if latest_obs and latest_obs.price_per_kg_or_l else None,
        "latest_date": str(latest_obs.observed_date) if latest_obs else None,
        "observations_count": len(obs_list),
        "min_price": min(prices) if prices else None,
        "max_price": max(prices) if prices else None,
        "aliases": alias_names,
        "created_at": prod.created_at.isoformat() if prod.created_at else "",
        "mercadona_online_id": prod.mercadona_online_id,
        "enriched_name": prod.enriched_name,
        "image_url": prod.image_url,
        "brand": prod.brand,
        "packaging": prod.packaging,
        "mercadona_url": prod.mercadona_url,
        "enrichment_status": prod.enrichment_status,
        "enrichment_confidence": float(prod.enrichment_confidence) if prod.enrichment_confidence is not None else None,
    }


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    household_id: Optional[uuid.UUID] = Query(None, description="Filtrar conteos por hogar"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the full product category hierarchy with active item counts."""
    await verify_household_access(household_id, current_user, db)
    return await CatalogService.list_categories(db, household_id=household_id)


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    household_id: Optional[uuid.UUID] = Query(None, description="Filtrar por ID de hogar"),
    category_id: Optional[str] = Query(None, description="Filtrar por ID de categoría"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre de producto o alias"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists normalized canonical products with their latest observed price and inflation metrics for the given household."""
    await verify_household_access(household_id, current_user, db)
    return await CatalogService.list_products(
        db,
        household_id=household_id,
        category_id=category_id,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves single product details and registered aliases."""
    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.category),
            selectinload(Product.aliases),
            selectinload(Product.price_observations),
        )
    )
    res = await db.execute(stmt)
    prod = res.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    obs_list = sorted(prod.price_observations, key=lambda o: o.observed_at)
    return format_product_dict(prod, obs_list=obs_list)


@router.get("/products/{product_id}/price-history", response_model=PriceHistoryResponse)
async def get_product_price_history(
    product_id: uuid.UUID,
    household_id: Optional[uuid.UUID] = Query(None, description="Filtrar por casa específica"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the immutable historical price observations for this product."""
    await verify_household_access(household_id, current_user, db)
    history = await CatalogService.get_product_price_history(db, product_id, household_id)
    if not history:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return history


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new canonical product and associates an optional initial alias."""
    try:
        cat_id = uuid.UUID(data.category_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de categoría inválido")

    # Check category existence
    cat = await db.get(Category, cat_id)
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")

    # Check unique canonical name
    existing = await db.execute(select(Product).where(Product.canonical_name == data.canonical_name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un producto con este nombre")

    product = Product(
        id=uuid.uuid4(),
        canonical_name=data.canonical_name,
        category_id=cat_id,
        default_unit=data.default_unit,
        format_description=data.format_description,
    )
    db.add(product)
    await db.flush()

    if data.initial_alias:
        raw_key = data.initial_alias.strip().upper()
        alias = ProductAlias(
            id=uuid.uuid4(),
            product_id=product.id,
            raw_name_normalized=raw_key,
            source="MERCADONA",
            is_verified=True,
        )
        db.add(alias)

    await db.commit()
    await db.refresh(product)

    return format_product_dict(
        product,
        category=cat,
        aliases=[data.initial_alias.strip().upper()] if data.initial_alias else [],
    )


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates product attributes (canonical name, category, default unit)."""
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    if data.canonical_name is not None:
        product.canonical_name = data.canonical_name
    if data.category_id is not None:
        try:
            cat_uuid = uuid.UUID(data.category_id)
            cat = await db.get(Category, cat_uuid)
            if not cat:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
            product.category_id = cat_uuid
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de categoría inválido")
    if data.default_unit is not None:
        product.default_unit = data.default_unit
    if data.format_description is not None:
        product.format_description = data.format_description

    await db.commit()
    await db.refresh(product)

    cat = await db.get(Category, product.category_id)
    return format_product_dict(product, category=cat)


@router.post("/products/{product_id}/aliases", response_model=ProductAliasResponse, status_code=status.HTTP_201_CREATED)
async def add_product_alias(
    product_id: uuid.UUID,
    data: ProductAliasCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registers an alternate ticket text alias mapped to this canonical product."""
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    raw_key = data.raw_name_normalized.strip().upper()
    existing = await db.execute(select(ProductAlias).where(ProductAlias.raw_name_normalized == raw_key))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este alias ya está asignado a un producto")

    alias = ProductAlias(
        id=uuid.uuid4(),
        product_id=product.id,
        raw_name_normalized=raw_key,
        source=data.source,
        is_verified=True,
    )
    db.add(alias)
    await db.commit()
    await db.refresh(alias)

    return {
        "id": str(alias.id),
        "product_id": str(alias.product_id),
        "raw_name_normalized": alias.raw_name_normalized,
        "source": alias.source,
        "is_verified": alias.is_verified,
    }


# =========================================================================
# Mercadona Online Catalog Integration Endpoints
# =========================================================================

@router.post("/mercadona/sync", response_model=MercadonaSyncResponse)
async def sync_mercadona_catalog(
    data: Optional[MercadonaSyncRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Downloads official catalog hierarchy and products from Mercadona Online for a given postal code."""
    postal_code = data.postal_code if data else None
    limit = data.limit_subcategories if data else None
    wh_code = MercadonaStorefrontClient.resolve_warehouse_code(postal_code)
    result = await MercadonaStorefrontClient.sync_catalog_to_db(db, warehouse_code=wh_code, limit_subcategories=limit)
    return result


@router.post("/mercadona/enrich", response_model=MercadonaEnrichResponse)
async def enrich_products(
    data: Optional[MercadonaEnrichRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Executes fuzzy matching between local canonical products and downloaded Mercadona catalog."""
    threshold = data.auto_threshold if data else 0.85
    result = await MercadonaMatcherService.enrich_all_household_products(db, auto_threshold=threshold)
    return result


@router.get("/mercadona/suggestions", response_model=List[MercadonaSuggestionItem])
async def get_mercadona_suggestions(
    household_id: Optional[uuid.UUID] = Query(None, description="Filtrar sugerencias por hogar"),
    limit_products: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns products that have moderate-confidence matching suggestions (score 0.50 - 0.84) or are unenriched for the household."""
    await verify_household_access(household_id, current_user, db)
    from app.domains.catalog.models import PriceObservation
    online_stmt = select(MercadonaOnlineProduct)
    online_res = await db.execute(online_stmt)
    all_online = online_res.scalars().all()

    stmt = (
        select(Product)
        .where(
            (Product.enrichment_status.notin_(["AUTO", "MANUALLY_CONFIRMED"]))
            | (Product.enrichment_status.is_(None))
        )
        .options(
            selectinload(Product.category),
            selectinload(Product.aliases),
            selectinload(Product.price_observations),
        )
    )
    if household_id:
        stmt = stmt.where(Product.price_observations.any(PriceObservation.household_id == household_id))

    res = await db.execute(stmt)
    products = res.scalars().all()

    items = []
    for p in products:
        if household_id:
            obs_list = [o for o in p.price_observations if o.household_id == household_id]
        else:
            obs_list = list(p.price_observations)
        obs_list = sorted(obs_list, key=lambda o: o.observed_at)
        latest_price = float(obs_list[-1].unit_price) if obs_list else None
        candidates = await MercadonaMatcherService.find_matches_for_product(
            db,
            p,
            reference_price=latest_price,
            candidate_pool=all_online,
            limit=4,
        )
        if candidates:
            items.append({
                "product": format_product_dict(p, obs_list=obs_list),
                "candidates": [
                    {
                        "mercadona_product": c[0],
                        "score": c[1],
                        "price_match": bool(
                            latest_price
                            and c[0].unit_price
                            and abs(float(latest_price) - float(c[0].unit_price)) <= 0.05
                        ),
                    }
                    for c in candidates
                ],
            })
            if len(items) >= limit_products:
                break
    return items


@router.post("/mercadona/confirm-match", response_model=ProductResponse)
async def confirm_match(
    data: MercadonaConfirmMatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually confirms binding between a canonical product and a Mercadona online item via ID or URL."""
    import re
    from app.domains.catalog.mercadona_client import MercadonaStorefrontClient
    from app.domains.receipts.models import ReceiptLine

    try:
        p_uuid = uuid.UUID(data.product_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de producto inválido")

    # Determine target Mercadona Online product ID
    target_online_id = None
    if data.mercadona_online_id and data.mercadona_online_id.strip():
        target_online_id = data.mercadona_online_id.strip()
    elif data.url_or_id and data.url_or_id.strip():
        raw_val = data.url_or_id.strip()
        url_match = re.search(r"/product/(\d+)", raw_val)
        if url_match:
            target_online_id = url_match.group(1)
        else:
            digit_match = re.search(r"(\d{3,8})", raw_val)
            if digit_match:
                target_online_id = digit_match.group(1)

    if not target_online_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar un ID o URL válida de Mercadona Online (ej: https://tienda.mercadona.es/product/14344/... o 14344).",
        )

    stmt = select(Product).where(Product.id == p_uuid).options(
        selectinload(Product.category),
        selectinload(Product.aliases),
        selectinload(Product.price_observations),
    )
    res = await db.execute(stmt)
    product = res.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    online_stmt = select(MercadonaOnlineProduct).where(MercadonaOnlineProduct.id == target_online_id)
    online_res = await db.execute(online_stmt)
    online_prod = online_res.scalar_one_or_none()

    # If not found in local cache, fetch directly from Mercadona API
    if not online_prod:
        online_prod = await MercadonaStorefrontClient.fetch_and_save_product_by_id(db, target_online_id)

    if not online_prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el producto en Mercadona con el identificador '{target_online_id}'.",
        )

    # Bind product
    product.mercadona_online_id = online_prod.id
    product.enriched_name = online_prod.display_name
    product.image_url = online_prod.thumbnail_url
    product.brand = online_prod.brand
    product.packaging = online_prod.packaging
    product.mercadona_url = online_prod.share_url
    product.enrichment_status = "MANUALLY_CONFIRMED"
    product.enrichment_confidence = 1.0

    # Auto-update category if currently 'otros' or undefined
    if (not product.category or product.category.slug == "otros") and online_prod.category_path:
        from app.domains.catalog.categorizer import classify_product
        inferred_slug = classify_product(
            product.canonical_name,
            [a.raw_name_normalized for a in product.aliases],
            mercadona_category_path=online_prod.category_path,
            mercadona_display_name=online_prod.display_name,
        )
        if inferred_slug != "otros":
            cat_stmt = select(Category).where(Category.slug == inferred_slug)
            cat_res = await db.execute(cat_stmt)
            new_cat = cat_res.scalar_one_or_none()
            if new_cat:
                product.category_id = new_cat.id

    # Ensure aliases are verified
    for a in product.aliases:
        a.is_verified = True

    # Propagate enriched attributes to existing receipt lines for this product
    lines_stmt = select(ReceiptLine).where(ReceiptLine.product_id == product.id)
    lines_res = await db.execute(lines_stmt)
    receipt_lines = lines_res.scalars().all()
    for rl in receipt_lines:
        rl.enriched_name = online_prod.display_name
        rl.image_url = online_prod.thumbnail_url
        rl.brand = online_prod.brand
        rl.packaging = online_prod.packaging

    await db.commit()

    # Re-fetch product with loaded relationships
    re_stmt = select(Product).where(Product.id == p_uuid).options(
        selectinload(Product.category),
        selectinload(Product.aliases),
        selectinload(Product.price_observations),
    )
    re_res = await db.execute(re_stmt)
    fresh_product = re_res.scalar_one()

    return format_product_dict(fresh_product)


@router.post("/mercadona/reject-match", response_model=ProductResponse)
async def reject_match(
    data: MercadonaRejectMatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rejects automatic or suggested match for a product."""
    try:
        p_uuid = uuid.UUID(data.product_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de producto inválido")

    stmt = select(Product).where(Product.id == p_uuid).options(
        selectinload(Product.category),
        selectinload(Product.aliases),
        selectinload(Product.price_observations),
    )
    res = await db.execute(stmt)
    product = res.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    product.mercadona_online_id = None
    product.enriched_name = None
    product.image_url = None
    product.brand = None
    product.packaging = None
    product.mercadona_url = None
    product.enrichment_status = "REJECTED"
    product.enrichment_confidence = None

    await db.commit()
    await db.refresh(product)
    return format_product_dict(product)


@router.get("/mercadona/search", response_model=List[MercadonaOnlineProductResponse])
async def search_mercadona_online(
    query: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Searches the local snapshot of Mercadona Online products."""
    search_term = f"%{query.strip().lower()}%"
    norm = normalize_string(query)
    normalized_term = f"%{norm}%" if norm else search_term
    slug_term = f"%{norm.replace(' ', '-')}%" if norm else search_term

    stmt = (
        select(MercadonaOnlineProduct)
        .where(
            or_(
                func.lower(MercadonaOnlineProduct.display_name).like(search_term),
                func.lower(MercadonaOnlineProduct.slug).like(slug_term),
                func.lower(MercadonaOnlineProduct.slug).like(normalized_term),
            )
        )
        .order_by(MercadonaOnlineProduct.display_name)
        .limit(limit)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/recategorize-all")
async def recategorize_all_products(
    only_otros: bool = Query(True, description="Si es True, sólo reclasifica productos que actualmente están en 'Otros'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Intelligently re-classifies products across system categories.
    Uses Mercadona Online category_path if linked, or keyword heuristics otherwise.
    """
    from collections import Counter
    from app.domains.catalog.categorizer import classify_product

    # Ensure categories are loaded
    categories_dict = await CatalogService.ensure_system_categories(db)

    stmt = (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.aliases),
        )
    )
    res = await db.execute(stmt)
    products = res.scalars().all()

    # Pre-fetch mercadona online products for those linked
    online_ids = [p.mercadona_online_id for p in products if p.mercadona_online_id]
    online_lookup = {}
    if online_ids:
        on_stmt = select(MercadonaOnlineProduct).where(MercadonaOnlineProduct.id.in_(online_ids))
        on_res = await db.execute(on_stmt)
        online_lookup = {item.id: item for item in on_res.scalars().all()}

    recategorized_count = 0
    counts = Counter()

    for p in products:
        current_slug = p.category.slug if p.category else "otros"

        if only_otros and current_slug != "otros":
            counts[current_slug] += 1
            continue

        online_prod = online_lookup.get(p.mercadona_online_id) if p.mercadona_online_id else None
        cat_path = online_prod.category_path if online_prod else None
        disp_name = online_prod.display_name if online_prod else None

        alias_texts = [a.raw_name_normalized for a in p.aliases]
        new_slug = classify_product(
            canonical_name=p.canonical_name,
            aliases=alias_texts,
            mercadona_category_path=cat_path,
            mercadona_display_name=disp_name,
        )

        target_cat = categories_dict.get(new_slug)
        if target_cat and target_cat.id != p.category_id:
            p.category_id = target_cat.id
            recategorized_count += 1

        counts[new_slug] += 1

    await db.commit()

    return {
        "status": "success",
        "total_products": len(products),
        "recategorized_count": recategorized_count,
        "distribution": dict(counts),
    }

