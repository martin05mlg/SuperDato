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


@pytest.mark.asyncio
async def test_mercadona_storefront_client_warehouse_and_brands():
    """Tests warehouse resolution from postal codes and private label detection."""
    from app.domains.catalog.mercadona_client import MercadonaStorefrontClient

    # Warehouse resolution
    assert MercadonaStorefrontClient.resolve_warehouse_code("50007") == "zar1"
    assert MercadonaStorefrontClient.resolve_warehouse_code("28001") == "mad1"
    assert MercadonaStorefrontClient.resolve_warehouse_code("08015") == "bcn1"
    assert MercadonaStorefrontClient.resolve_warehouse_code(None) == "zar1"
    assert MercadonaStorefrontClient.resolve_warehouse_code("") == "zar1"

    # Brand detection
    assert MercadonaStorefrontClient.extract_brand("Leche semidesnatada Hacendado botella 1 L") == "Hacendado"
    assert MercadonaStorefrontClient.extract_brand("Crema hidratante Deliplus tarro") == "Deliplus"
    assert MercadonaStorefrontClient.extract_brand("Lavavajillas concentrado Bosque Verde") == "Bosque Verde"
    assert MercadonaStorefrontClient.extract_brand("Comida húmeda gatos Compy") == "Compy"
    assert MercadonaStorefrontClient.extract_brand("Coca-Cola Original 330 ml") is None


@pytest.mark.asyncio
async def test_mercadona_matcher_service(db_session: AsyncSession):
    """Tests string normalization, abbreviation expansion, fuzzy scoring, and candidate search."""
    from app.domains.catalog.matcher import MercadonaMatcherService, normalize_string, token_similarity
    from app.domains.catalog.models import MercadonaOnlineProduct

    # Normalization & abbreviations
    assert "desodorante" in normalize_string("DEO ROLL-ON")
    assert "semidesnatada" in normalize_string("LECHE SEMIDESN")

    # Similarity scoring
    sim = token_similarity("LECHE SEMIDESN HACENDADO", "Leche semidesnatada Hacendado brik 1 L")
    assert sim >= 0.85

    # Seed an online product
    online_p = MercadonaOnlineProduct(
        id="998877",
        display_name="Leche semidesnatada Hacendado brik 1 L",
        slug="leche-semidesnatada-hacendado-brik-1-l",
        brand="Hacendado",
        packaging="Brik 1 L",
        thumbnail_url="https://prod-mercadona.imgix.net/images/sample.jpg",
        share_url="https://tienda.mercadona.es/product/998877",
        unit_price=0.95,
        warehouse_code="zar1",
    )
    db_session.add(online_p)

    # Seed a local product
    cat = await CatalogService.ensure_system_categories(db_session)
    local_p = Product(
        id=uuid.uuid4(),
        canonical_name="Leche Semidesnatada Hacendado",
        category_id=cat["lacteos-y-huevos"].id,
        default_unit="ud",
    )
    db_session.add(local_p)
    await db_session.commit()

    # Find matches
    matches = await MercadonaMatcherService.find_matches_for_product(db_session, local_p, reference_price=0.95)
    assert len(matches) >= 1
    best, score = matches[0]
    assert best.id == "998877"
    assert score >= 0.85

    # Run household auto-enrichment
    summary = await MercadonaMatcherService.enrich_all_household_products(db_session, auto_threshold=0.85)
    assert summary["auto_enriched_count"] >= 1

    # Verify local_p is enriched
    await db_session.refresh(local_p)
    assert local_p.mercadona_online_id == "998877"
    assert local_p.image_url == "https://prod-mercadona.imgix.net/images/sample.jpg"
    assert local_p.enrichment_status == "AUTO"


@pytest.mark.asyncio
async def test_mercadona_api_manual_binding_and_search(client: AsyncClient, db_session: AsyncSession):
    """Tests search, suggestions, confirm match, and reject match endpoints."""
    from app.domains.catalog.models import MercadonaOnlineProduct

    # 1. Seed online product in DB
    online_item = MercadonaOnlineProduct(
        id="112233",
        display_name="Galletas María Hacendado paquete 800 g",
        slug="galletas-maria-hacendado",
        brand="Hacendado",
        packaging="Paquete 800 g",
        thumbnail_url="https://prod-mercadona.imgix.net/images/galletas.jpg",
        share_url="https://tienda.mercadona.es/product/112233",
        unit_price=1.60,
        warehouse_code="zar1",
    )
    db_session.add(online_item)

    # Seed local product
    cat = await CatalogService.ensure_system_categories(db_session)
    local_item = Product(
        id=uuid.uuid4(),
        canonical_name="Galleta Maria",
        category_id=cat["despensa-y-conservas"].id,
        default_unit="ud",
    )
    db_session.add(local_item)
    await db_session.commit()

    # 2. GET /api/v1/catalog/mercadona/search?query=maria
    search_res = await client.get("/api/v1/catalog/mercadona/search?query=maria")
    assert search_res.status_code == 200
    search_results = search_res.json()
    assert any(p["id"] == "112233" for p in search_results)

    # 3. POST /api/v1/catalog/mercadona/confirm-match
    confirm_res = await client.post("/api/v1/catalog/mercadona/confirm-match", json={
        "product_id": str(local_item.id),
        "mercadona_online_id": "112233",
    })
    assert confirm_res.status_code == 200
    confirmed_data = confirm_res.json()
    assert confirmed_data["enrichment_status"] == "MANUALLY_CONFIRMED"
    assert confirmed_data["image_url"] == "https://prod-mercadona.imgix.net/images/galletas.jpg"
    assert confirmed_data["brand"] == "Hacendado"

    # 4. POST /api/v1/catalog/mercadona/reject-match
    reject_res = await client.post("/api/v1/catalog/mercadona/reject-match", json={
        "product_id": str(local_item.id),
    })
    assert reject_res.status_code == 200
    rejected_data = reject_res.json()
    assert rejected_data["enrichment_status"] == "REJECTED"
    assert rejected_data["image_url"] is None


@pytest.mark.asyncio
async def test_intelligent_categorizer_and_persistence(client: AsyncClient, db_session: AsyncSession):
    """
    Tests:
    1. Intelligent classification heuristics for vegetables, fish, meats, dairy, bread, etc.
    2. POST /catalog/recategorize-all endpoint.
    3. Product category update persistence across alias lookups.
    """
    from app.domains.catalog.categorizer import classify_product

    # 1. Direct categorizer tests
    assert classify_product("BORRAJA") == "frutas-y-verduras"
    assert classify_product("ACELGA LIMPIA") == "frutas-y-verduras"
    assert classify_product("CARDO TROCEADO") == "frutas-y-verduras"
    assert classify_product("MERLUZA FILETES") == "pescaderia"
    assert classify_product("PECHUGA POLLO") == "carniceria-y-charcuteria"
    assert classify_product("CHORIZO EXTRA") == "carniceria-y-charcuteria"
    assert classify_product("LECHE ENTERA 1L") == "lacteos-y-huevos"
    assert classify_product("QUESO LONCHAS GOUDA") == "lacteos-y-huevos"
    assert classify_product("PAN BARRA INTEGRAL") == "panaderia-y-pasteleria"
    assert classify_product("ARROZ REDONDO") == "despensa-y-conservas"
    assert classify_product("CERVEZA RADLER") == "bebidas-y-refrescos"
    assert classify_product("DETERGENTE LAVADORA") == "limpieza-y-hogar"

    # 2. Database recategorize-all endpoint
    cat = await CatalogService.ensure_system_categories(db_session)
    otros_cat = cat["otros"]

    # Create a product forced into 'otros'
    sample_prod = Product(
        id=uuid.uuid4(),
        canonical_name="Cardo Troceado",
        category_id=otros_cat.id,
        default_unit="ud",
    )
    db_session.add(sample_prod)
    db_session.add(ProductAlias(
        id=uuid.uuid4(),
        product_id=sample_prod.id,
        raw_name_normalized="CARDO TROCEADO",
        source="MERCADONA",
        is_verified=False,
    ))
    await db_session.commit()

    # Call /api/v1/catalog/recategorize-all
    recat_res = await client.post("/api/v1/catalog/recategorize-all?only_otros=true")
    assert recat_res.status_code == 200
    recat_data = recat_res.json()
    assert recat_data["status"] == "success"
    assert recat_data["recategorized_count"] >= 1

    # Verify sample_prod was recategorized to Frutas y Verduras
    await db_session.refresh(sample_prod)
    assert sample_prod.category_id == cat["frutas-y-verduras"].id

    # 3. User manual edit persistence
    # Suppose user manually changes it to 'platos-preparados'
    update_res = await client.patch(f"/api/v1/catalog/products/{sample_prod.id}", json={
        "category_id": str(cat["platos-preparados"].id),
    })
    assert update_res.status_code == 200
    assert update_res.json()["category_name"] == "Platos Preparados"

    # 4. Verify future receipt purchase with same alias keeps the user's category
    resolved_prod = await CatalogService.get_or_create_product_for_line(
        db=db_session,
        raw_description="CARDO TROCEADO",
    )
    assert resolved_prod.id == sample_prod.id
    assert resolved_prod.category_id == cat["platos-preparados"].id



