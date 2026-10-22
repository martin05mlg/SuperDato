import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
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
async def list_categories(db: AsyncSession = Depends(get_db)):
    """Returns the full product category hierarchy with active item counts."""
    return await CatalogService.list_categories(db)


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    category_id: Optional[str] = Query(None, description="Filtrar por ID de categoría"),
    search: Optional[str] = Query(None, description="Búsqueda por nombre de producto o alias"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Lists normalized canonical products with their latest observed price and inflation metrics."""
    return await CatalogService.list_products(
        db,
        category_id=category_id,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
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
    db: AsyncSession = Depends(get_db),
):
    """Returns the immutable historical price observations for this product."""
    history = await CatalogService.get_product_price_history(db, product_id, household_id)
    if not history:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return history


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
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
    db: AsyncSession = Depends(get_db),
):
    """Executes fuzzy matching between local canonical products and downloaded Mercadona catalog."""
    threshold = data.auto_threshold if data else 0.85
    result = await MercadonaMatcherService.enrich_all_household_products(db, auto_threshold=threshold)
    return result


@router.get("/mercadona/suggestions", response_model=List[MercadonaSuggestionItem])
async def get_mercadona_suggestions(
    limit_products: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Returns products that have moderate-confidence matching suggestions (score 0.50 - 0.84) or are unenriched."""
    stmt = (
        select(Product)
        .where(
            (Product.enrichment_status != "MANUALLY_CONFIRMED")
            | (Product.enrichment_status.is_(None))
        )
        .options(
            selectinload(Product.category),
            selectinload(Product.aliases),
            selectinload(Product.price_observations),
        )
        .limit(limit_products)
    )
    res = await db.execute(stmt)
    products = res.scalars().all()

    items = []
    for p in products:
        obs_list = sorted(p.price_observations, key=lambda o: o.observed_at)
        latest_price = float(obs_list[-1].unit_price) if obs_list else None
        candidates = await MercadonaMatcherService.find_matches_for_product(db, p, reference_price=latest_price, limit=4)
        if candidates:
            items.append({
                "product": format_product_dict(p, obs_list=obs_list),
                "candidates": [
                    {
                        "mercadona_product": c[0],
                        "score": c[1],
                    }
                    for c in candidates
                ],
            })
    return items


@router.post("/mercadona/confirm-match", response_model=ProductResponse)
async def confirm_match(
    data: MercadonaConfirmMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually confirms binding between a canonical product and a Mercadona online item."""
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

    online_stmt = select(MercadonaOnlineProduct).where(MercadonaOnlineProduct.id == data.mercadona_online_id)
    online_res = await db.execute(online_stmt)
    online_prod = online_res.scalar_one_or_none()
    if not online_prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto de Mercadona Online no encontrado")

    product.mercadona_online_id = online_prod.id
    product.enriched_name = online_prod.display_name
    product.image_url = online_prod.thumbnail_url
    product.brand = online_prod.brand
    product.packaging = online_prod.packaging
    product.mercadona_url = online_prod.share_url
    product.enrichment_status = "MANUALLY_CONFIRMED"
    product.enrichment_confidence = 1.0

    await db.commit()
    await db.refresh(product)
    return format_product_dict(product)


@router.post("/mercadona/reject-match", response_model=ProductResponse)
async def reject_match(
    data: MercadonaRejectMatchRequest,
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

