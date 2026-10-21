import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_receipts_returns_samples(client: AsyncClient):
    response = await client.get("/api/v1/receipts")
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
async def test_get_receipt_detail(client: AsyncClient):
    # List first
    list_res = await client.get("/api/v1/receipts")
    receipt_id = list_res.json()[0]["id"]

    detail_res = await client.get(f"/api/v1/receipts/{receipt_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["lines"]) > 0
    assert len(detail["tax_lines"]) > 0
    # Check that weighed items have weight_in_kg
    weighed_lines = [l for l in detail["lines"] if l["is_weighed_item"]]
    assert len(weighed_lines) > 0
    assert weighed_lines[0]["unit_of_measure"] == "kg"


@pytest.mark.asyncio
async def test_analytics_summary(client: AsyncClient):
    response = await client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["receipt_count"] >= 2
    assert summary["total_spend"] > 0
    assert summary["average_ticket"] > 0


@pytest.mark.asyncio
async def test_category_distribution(client: AsyncClient):
    response = await client.get("/api/v1/analytics/category-distribution")
    assert response.status_code == 200
    dist = response.json()
    assert len(dist) > 0
    assert "category_name" in dist[0]
    assert "total_spend" in dist[0]

