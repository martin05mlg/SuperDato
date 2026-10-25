import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_receipts_returns_samples(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/receipts")
    assert response.status_code == 200
    receipts = response.json()
    assert len(receipts) >= 2
    # Verify first ticket structure
    r = receipts[0]
    assert "invoice_number" in r
    assert "total_amount" in r
    assert r["company_cif"] == "A-46103834"
    assert r["status"] == "PROCESSED"


@pytest.mark.asyncio
async def test_get_receipt_detail(auth_client: AsyncClient):
    # List first
    list_res = await auth_client.get("/api/v1/receipts")
    receipt_id = list_res.json()[0]["id"]

    detail_res = await auth_client.get(f"/api/v1/receipts/{receipt_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["lines"]) > 0
    assert len(detail["tax_lines"]) > 0
    assert detail["lines"][0]["product_name"] is not None
    assert detail["lines"][0]["category_name"] is not None
    assert detail["tax_lines"][0]["id"] is not None
    # Check that weighed items have weight_in_kg
    weighed_lines = [l for l in detail["lines"] if l["is_weighed_item"]]
    assert len(weighed_lines) > 0
    assert weighed_lines[0]["unit_of_measure"] == "kg"


@pytest.mark.asyncio
async def test_update_receipt_line_via_api(auth_client: AsyncClient):
    list_res = await auth_client.get("/api/v1/receipts")
    receipt_id = list_res.json()[0]["id"]

    detail_res = await auth_client.get(f"/api/v1/receipts/{receipt_id}")
    line_id = detail_res.json()["lines"][0]["id"]

    patch_res = await auth_client.patch(
        f"/api/v1/receipts/{receipt_id}/lines/{line_id}",
        json={"unit_price": 12.50, "line_total": 12.50},
    )
    assert patch_res.status_code == 200
    patched_line = patch_res.json()
    assert patched_line["unit_price"] == 12.50
    assert patched_line["is_manual_override"] is True
    assert patched_line["validation_status"] == "MANUALLY_EDITED"


@pytest.mark.asyncio
async def test_analytics_summary(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["receipt_count"] >= 2
    assert summary["total_spend"] > 0
    assert summary["average_ticket"] > 0


@pytest.mark.asyncio
async def test_category_distribution(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/analytics/category-distribution")
    assert response.status_code == 200
    dist = response.json()
    assert len(dist) > 0
    assert "category_name" in dist[0]
    assert "total_spend" in dist[0]


@pytest.mark.asyncio
async def test_top_products_analytics(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/analytics/top-products?limit=5")
    assert response.status_code == 200
    top = response.json()
    assert len(top) > 0
    assert "product_name" in top[0]
    assert "total_spend" in top[0]
    assert top[0]["total_spend"] > 0


@pytest.mark.asyncio
async def test_analytics_with_date_range(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/analytics/summary?start_date=2026-01-01&end_date=2026-12-31")
    assert response.status_code == 200
    data = response.json()
    assert "total_spend" in data
    assert "receipt_count" in data


@pytest.mark.asyncio
async def test_delete_receipt_and_prevent_sample_reseed(auth_client: AsyncClient):
    # 1. List receipts
    list_res = await auth_client.get("/api/v1/receipts")
    assert list_res.status_code == 200
    receipts = list_res.json()
    assert len(receipts) > 0

    receipt_to_delete = receipts[0]
    r_id = receipt_to_delete["id"]

    # 2. Delete the receipt
    del_res = await auth_client.delete(f"/api/v1/receipts/{r_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 3. Verify it is gone
    get_res = await auth_client.get(f"/api/v1/receipts/{r_id}")
    assert get_res.status_code == 404

    # 4. Deleting non-existent returns 404
    del_res2 = await auth_client.delete(f"/api/v1/receipts/{r_id}")
    assert del_res2.status_code == 404


@pytest.mark.asyncio
async def test_pdf_receipt_extractor_numeric_titles_parsing():
    """
    Verifies that product names containing numbers (e.g. Alcohol 96, Vino 2022)
    are not erroneously parsed as unit prices.
    """
    from app.domains.receipts.extractor.pdf_parser import PDFReceiptExtractor

    raw_ticket_text = """
    MERCADONA, S.A. A-46103834
    C/ TEST 123
    50001 ZARAGOZA
    FACTURA SIMPLIFICADA: 4534-012-123456
    15/05/2026 18:30 OP: 999
    
    Descripción P. Unit Importe
    1 ALCOHOL ETILICO 96 0,80
    2 DEO ROLL-ON ALOE 0,90 1,80
    2 ALCOHOL ETILICO 96 0,80 1,60
    1 VINO TINTO COSECHA 2022 3,50
    TOTAL (€) 7,70
    TARJ. BANCARIA: **** **** **** 1234
    """

    data = PDFReceiptExtractor.extract_from_text(raw_ticket_text)
    lines = data["lines"]
    assert len(lines) == 4

    # 1. Alcohol 96 single unit
    assert lines[0]["raw_description"] == "ALCOHOL ETILICO 96"
    assert lines[0]["quantity"] == 1.0
    assert lines[0]["unit_price"] == 0.80
    assert lines[0]["line_total"] == 0.80

    # 2. Multi-unit deo
    assert lines[1]["raw_description"] == "DEO ROLL-ON ALOE"
    assert lines[1]["quantity"] == 2.0
    assert lines[1]["unit_price"] == 0.90
    assert lines[1]["line_total"] == 1.80

    # 3. Multi-unit alcohol 96
    assert lines[2]["raw_description"] == "ALCOHOL ETILICO 96"
    assert lines[2]["quantity"] == 2.0
    assert lines[2]["unit_price"] == 0.80
    assert lines[2]["line_total"] == 1.60

    # 4. Single unit vino 2022
    assert lines[3]["raw_description"] == "VINO TINTO COSECHA 2022"
    assert lines[3]["quantity"] == 1.0
    assert lines[3]["unit_price"] == 3.50
    assert lines[3]["line_total"] == 3.50


@pytest.mark.asyncio
async def test_heal_inconsistent_receipt_line_prices(db_session):
    """
    Verifies that the auto-healing routine repairs corrupt receipt lines
    where quantity == 1 but unit_price was stored as 96.00 instead of 0.80.
    """
    import uuid
    from datetime import date, datetime, timezone
    from app.core.bootstrap import heal_inconsistent_receipt_line_prices
    from app.domains.receipts.models import Receipt, ReceiptLine
    from app.domains.catalog.models import Product, PriceObservation, Category
    from app.domains.catalog.services import CatalogService

    cats = await CatalogService.ensure_system_categories(db_session)

    # Setup parent receipt
    r_id = uuid.uuid4()
    receipt = Receipt(
        id=r_id,
        invoice_number="9999-001-999999",
        purchase_date=date(2025, 2, 28),
        purchase_time="12:00",
        purchase_datetime=datetime(2025, 2, 28, 12, 0, tzinfo=timezone.utc),
        total_amount=0.80,
        deduplication_hash="test-dedup-hash-heal",
    )
    db_session.add(receipt)

    line_id = uuid.uuid4()
    prod_id = uuid.uuid4()
    prod = Product(
        id=prod_id,
        canonical_name="Alcohol Etilico 96",
        category_id=cats["cuidado-personal-y-perfumeria"].id,
        default_unit="ud",
    )
    db_session.add(prod)

    # Corrupt line with 96.00 unit price and 0.80 total
    corrupt_line = ReceiptLine(
        id=line_id,
        receipt_id=r_id,
        line_order=1,
        raw_description="ALCOHOL ETILICO",
        product_id=prod_id,
        quantity=1.0,
        unit_price=96.00,  # Corrupt value!
        line_total=0.80,
        discount_amount=0.00,
    )
    db_session.add(corrupt_line)

    obs = PriceObservation(
        id=uuid.uuid4(),
        product_id=prod_id,
        receipt_line_id=line_id,
        unit_price=96.00,  # Corrupt value!
        observed_date=date(2025, 2, 28),
        observed_at=datetime(2025, 2, 28, 12, 0, tzinfo=timezone.utc),
        store_code="4534",
    )
    db_session.add(obs)
    await db_session.commit()

    # Run healer
    healed = await heal_inconsistent_receipt_line_prices(db_session)
    assert healed >= 1

    # Verify line and observation were corrected
    await db_session.refresh(corrupt_line)
    await db_session.refresh(obs)

    assert float(corrupt_line.unit_price) == 0.80
    assert float(corrupt_line.line_total) == 0.80
    assert corrupt_line.raw_description == "ALCOHOL ETILICO 96"
    assert float(obs.unit_price) == 0.80



