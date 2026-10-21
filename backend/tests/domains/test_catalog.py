import uuid
from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.models import Category, PriceObservation, Product, ProductAlias
from app.domains.catalog.services import CatalogService
from app.domains.households.models import Household
from app.domains.receipts.services import ReceiptService


@pytest.mark.asyncio
async def test_category_seeding(db_session: AsyncSession):
    """Verifies default categories are seeded idempotently with slugs, icons, and colors."""
    categories = await CatalogService.ensure_system_categories(db_session)
    assert len(categories) >= 12
    assert "frutas-y-verduras" in categories
    assert "carniceria-y-charcuteria" in categories
    assert categories["frutas-y-verduras"].icon == "apple"
    assert categories["frutas-y-verduras"].color_hex == "#10B981"

    # Second execution must be idempotent and not create duplicates
    categories_again = await CatalogService.ensure_system_categories(db_session)
    assert len(categories_again) == len(categories)


@pytest.mark.asyncio
async def test_product_normalization_and_alias_mapping(db_session: AsyncSession):
    """Tests normalisation of raw ticket names to canonical products and alias creation."""
    # 1. Normalizing standard text
    raw_key, canonical = CatalogService.normalize_description("DEO ROLL-ON ALOE")
    assert raw_key == "DEO ROLL-ON ALOE"
    assert canonical == "Deo Roll-on Aloe"

    # 2. Stripping numeric quantity prefixes
    raw_key2, canonical2 = CatalogService.normalize_description("1 CIRUELA AMARILLA")
    assert raw_key2 == "CIRUELA AMARILLA"
    assert canonical2 == "Ciruela Amarilla"

    # 3. Create product for line in DB
    prod1 = await CatalogService.get_or_create_product_for_line(
        db=db_session,
        raw_description="DEO ROLL-ON ALOE",
        category_hint="Cuidado Personal",
    )
    assert prod1.canonical_name == "Deo Roll-on Aloe"

    # 4. Subsequent line with same raw description reuses existing product and alias
    prod2 = await CatalogService.get_or_create_product_for_line(
        db=db_session,
        raw_description="DEO ROLL-ON ALOE",
    )
    assert prod2.id == prod1.id

    # Verify alias exists in DB
    aliases = (await db_session.execute(select(ProductAlias).where(ProductAlias.product_id == prod1.id))).scalars().all()
    assert len(aliases) == 1
    assert aliases[0].raw_name_normalized == "DEO ROLL-ON ALOE"


@pytest.mark.asyncio
async def test_immutable_price_observations_and_history(db_session: AsyncSession):
    """Tests recording chronological price observations and retrieving inflation tracking series."""
    # Setup household and product
    hh = Household(id=uuid.uuid4(), name="Casa Prueba", currency="EUR", created_by_user_id=uuid.uuid4())
    db_session.add(hh)
    await db_session.flush()

    prod = await CatalogService.get_or_create_product_for_line(
        db=db_session,
        raw_description="LECHE ENTERA 1L",
        category_hint="Lácteos y Huevos",
    )

    # Observation 1: 0.90 € on 2026-09-01
    line1_id = uuid.uuid4()
    obs1 = await CatalogService.record_price_observation(
        db=db_session,
        household_id=hh.id,
        product_id=prod.id,
        receipt_line_id=line1_id,
        observed_at=datetime(2026, 9, 1, 10, 30, tzinfo=timezone.utc),
        observed_date=date(2026, 9, 1),
        unit_price=0.90,
        store_code="4534",
    )
    assert float(obs1.unit_price) == 0.90

    # Observation 2: 1.05 € on 2026-10-15 (Inflation of +16.67%)
    line2_id = uuid.uuid4()
    obs2 = await CatalogService.record_price_observation(
        db=db_session,
        household_id=hh.id,
        product_id=prod.id,
        receipt_line_id=line2_id,
        observed_at=datetime(2026, 10, 15, 14, 20, tzinfo=timezone.utc),
        observed_date=date(2026, 10, 15),
        unit_price=1.05,
        store_code="4534",
    )
    assert float(obs2.unit_price) == 1.05

    # Retrieve history
    history = await CatalogService.get_product_price_history(db_session, prod.id)
    assert history is not None
    assert len(history["observations"]) == 2
    assert history["current_price"] == 1.05
    assert history["min_price"] == 0.90
    assert history["max_price"] == 1.05
    assert history["price_change_pct"] == 16.67


@pytest.mark.asyncio
async def test_manual_override_on_receipt_line():
    """Verifies manual line edit marks is_manual_override=True and validation_status='MANUALLY_EDITED'."""
    receipts = ReceiptService.get_all_receipts()
    assert len(receipts) > 0
    receipt = receipts[0]
    line = receipt["lines"][0]

    line_id = line["id"]
    updated = ReceiptService.update_receipt_line(
        receipt_id=receipt["id"],
        line_id=line_id,
        updates={"unit_price": 9.99, "line_total": 9.99},
    )

    assert updated is not None
    assert updated["unit_price"] == 9.99
    assert updated["is_manual_override"] is True
    assert updated["validation_status"] == "MANUALLY_EDITED"
    assert receipt["is_manual_override"] is True


@pytest.mark.asyncio
async def test_catalog_api_endpoints(client: AsyncClient):
    """Tests the REST API routes for categories, products, aliases, and price history."""
    # 1. GET /api/v1/catalog/categories
    cat_res = await client.get("/api/v1/catalog/categories")
    assert cat_res.status_code == 200
    categories = cat_res.json()
    assert len(categories) >= 12
    cat_id = categories[0]["id"]

    # 2. POST /api/v1/catalog/products
    new_prod_res = await client.post("/api/v1/catalog/products", json={
        "canonical_name": "Aceite de Oliva Virgen Extra 1L",
        "category_id": cat_id,
        "default_unit": "ud",
        "format_description": "Botella 1L",
        "initial_alias": "ACEITE OLIVA VIRGEN EXTRA",
    })
    assert new_prod_res.status_code == 201
    prod_data = new_prod_res.json()
    product_id = prod_data["id"]
    assert prod_data["canonical_name"] == "Aceite de Oliva Virgen Extra 1L"

    # 3. GET /api/v1/catalog/products
    list_res = await client.get("/api/v1/catalog/products")
    assert list_res.status_code == 200
    products = list_res.json()
    assert any(p["id"] == product_id for p in products)

    # 4. POST /api/v1/catalog/products/{id}/aliases
    alias_res = await client.post(f"/api/v1/catalog/products/{product_id}/aliases", json={
        "raw_name_normalized": "AOVE 1L HACENDADO",
        "source": "MERCADONA",
    })
    assert alias_res.status_code == 201
    assert alias_res.json()["raw_name_normalized"] == "AOVE 1L HACENDADO"

    # 5. GET /api/v1/catalog/products/{id}/price-history
    history_res = await client.get(f"/api/v1/catalog/products/{product_id}/price-history")
    assert history_res.status_code == 200
    assert history_res.json()["product_name"] == "Aceite de Oliva Virgen Extra 1L"

