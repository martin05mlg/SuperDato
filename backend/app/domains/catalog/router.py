import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.domains.catalog.models import Category, Product, ProductAlias
from app.domains.catalog.schemas import (
    CategoryResponse,
    PriceHistoryResponse,
    ProductAliasCreate,
    ProductAliasResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.domains.catalog.services import CatalogService

router = APIRouter(prefix="/catalog", tags=["Catálogo y Precios"])


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
    latest_obs = obs_list[-1] if obs_list else None
    prices = [float(o.unit_price) for o in obs_list]

    return {
        "id": str(prod.id),
        "canonical_name": prod.canonical_name,
        "category_id": str(prod.category_id),
        "category_name": prod.category.name if prod.category else "Otros",
        "category_color": prod.category.color_hex if prod.category else "#6B7280",
        "default_unit": prod.default_unit,
        "format_description": prod.format_description,
        "latest_price": float(latest_obs.unit_price) if latest_obs else None,
        "latest_price_per_kg_or_l": float(latest_obs.price_per_kg_or_l) if latest_obs and latest_obs.price_per_kg_or_l else None,
        "latest_date": str(latest_obs.observed_date) if latest_obs else None,
        "observations_count": len(obs_list),
        "min_price": min(prices) if prices else None,
        "max_price": max(prices) if prices else None,
        "aliases": [a.raw_name_normalized for a in prod.aliases],
        "created_at": prod.created_at.isoformat() if prod.created_at else "",
    }


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

    return {
        "id": str(product.id),
        "canonical_name": product.canonical_name,
        "category_id": str(product.category_id),
        "category_name": cat.name,
        "category_color": cat.color_hex or "#6B7280",
        "default_unit": product.default_unit,
        "format_description": product.format_description,
        "latest_price": None,
        "latest_price_per_kg_or_l": None,
        "latest_date": None,
        "observations_count": 0,
        "min_price": None,
        "max_price": None,
        "aliases": [data.initial_alias.strip().upper()] if data.initial_alias else [],
        "created_at": product.created_at.isoformat(),
    }


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
    return {
        "id": str(product.id),
        "canonical_name": product.canonical_name,
        "category_id": str(product.category_id),
        "category_name": cat.name if cat else "Otros",
        "category_color": cat.color_hex if cat else "#6B7280",
        "default_unit": product.default_unit,
        "format_description": product.format_description,
        "latest_price": None,
        "latest_price_per_kg_or_l": None,
        "latest_date": None,
        "observations_count": 0,
        "min_price": None,
        "max_price": None,
        "aliases": [],
        "created_at": product.created_at.isoformat() if product.created_at else "",
    }


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

