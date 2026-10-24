import uuid
from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analytics.services import AnalyticsService
from app.domains.catalog.matcher import MercadonaMatcherService
from app.domains.catalog.models import MercadonaOnlineProduct, Product
from app.domains.catalog.services import CatalogService
from app.domains.households.models import Household, HouseholdMembership
from app.domains.receipts.models import Receipt, ReceiptLine
from app.domains.receipts.services import ReceiptService


@pytest.mark.asyncio
async def test_bug01_budget_preserved_when_no_receipts_in_date_filter(
    client: AsyncClient, db_session: AsyncSession
):
    """BUG-01: When filtering by a date range with 0 purchases, monthly budget KPIs must still be present."""
    # 1. Create a user and household with a monthly budget configured
    user_res = await client.post("/api/v1/auth/register", json={
        "email": "budget_test@ejemplo.com",
        "password": "PasswordSegura123!",
        "full_name": "Budget User",
        "registration_token": "TEST-TOKEN-1234",
    })
    token = user_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    h_res = await client.get("/api/v1/households", headers=headers)
    hh_id = h_res.json()[0]["id"]

    # Configure 450.00 EUR budget
    patch_hh = await client.patch(
        f"/api/v1/households/{hh_id}",
        json={"settings": {"monthly_budget": 450.00}},
        headers=headers,
    )
    assert patch_hh.status_code == 200

    # 2. Query summary with a future or past date range that has 0 receipts
    summary_empty = await client.get(
        f"/api/v1/analytics/summary?household_id={hh_id}&start_date=2020-01-01&end_date=2020-01-10",
        headers=headers,
    )
    assert summary_empty.status_code == 200
    data = summary_empty.json()

    # Must preserve the household's budget metrics instead of returning null
    assert data["receipt_count"] == 0
    assert data["monthly_budget"] == 450.00
    assert data["current_month_spend"] is not None
    assert data["budget_spent_pct"] is not None
    assert data["budget_remaining"] is not None


@pytest.mark.asyncio
async def test_perf01_batch_price_observations_in_receipt_detail(
    client: AsyncClient, db_session: AsyncSession
):
    """PERF-01: Verifies that single-batch price observation lookup computes inflation deltas correctly."""
    hh = Household(id=uuid.uuid4(), name="Casa Perf", currency="EUR", created_by_user_id=uuid.uuid4())
    db_session.add(hh)
    await db_session.flush()

    prod = await CatalogService.get_or_create_product_for_line(
        db=db_session,
        raw_description="LECHE ENTERA 1L PERF",
        category_hint="Lácteos y Huevos",
    )

    # Prior observation: 1.00 EUR on 2026-09-01
    await CatalogService.record_price_observation(
        db=db_session,
        household_id=hh.id,
        product_id=prod.id,
        receipt_line_id=uuid.uuid4(),
        observed_at=datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc),
        observed_date=date(2026, 9, 1),
        unit_price=1.00,
    )

    # Current receipt: 1.20 EUR on 2026-10-15 (+20.0%)
    receipt_id = uuid.uuid4()
    receipt = Receipt(
        id=receipt_id,
        household_id=hh.id,
        company_name="MERCADONA, S.A.",
        company_cif="A-46103834",
        invoice_number="PERF-001",
        purchase_datetime=datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc),
        purchase_date=date(2026, 10, 15),
        purchase_time="12:00",
        total_amount=1.20,
        deduplication_hash=f"dedup-perf-{uuid.uuid4()}",
        assignment_status="ASSIGNED",
    )
    db_session.add(receipt)
    line = ReceiptLine(
        id=uuid.uuid4(),
        receipt_id=receipt_id,
        line_order=1,
        raw_description="LECHE ENTERA 1L PERF",
        product_id=prod.id,
        quantity=1.0,
        unit_of_measure="ud",
        unit_price=1.20,
        line_total=1.20,
    )
    db_session.add(line)
    await db_session.commit()

    # Fetch receipt detail
    detail = await ReceiptService.get_receipt_detail(db_session, str(receipt_id))
    assert detail is not None
    assert len(detail["lines"]) == 1
    line_out = detail["lines"][0]
    assert line_out["previous_unit_price"] == 1.00
    assert line_out["price_change_pct"] == 20.0


@pytest.mark.asyncio
async def test_perf02_matcher_cache_and_fast_lookup(db_session: AsyncSession):
    """PERF-02: Matcher pre-tokenized pool caches items and handles invalidation correctly."""
    MercadonaMatcherService.invalidate_cache()
    assert MercadonaMatcherService._CACHED_ONLINE_POOL is None

    # Seed an item
    online_p = MercadonaOnlineProduct(
        id="888777",
        display_name="Cereales Copos de Maiz Hacendado caja 500 g",
        slug="cereales-copos-de-maiz-hacendado-caja-500-g",
        brand="Hacendado",
        packaging="Caja 500 g",
        thumbnail_url="https://prod-mercadona.imgix.net/sample.jpg",
        unit_price=1.50,
        warehouse_code="zar1",
    )
    db_session.add(online_p)
    await db_session.commit()

    # Calling get_cached_pool populates the memory cache
    pool = await MercadonaMatcherService.get_cached_pool(db_session)
    assert len(pool) >= 1
    assert MercadonaMatcherService._CACHED_ONLINE_POOL is not None

    # Invalidation clears the memory cache
    MercadonaMatcherService.invalidate_cache()
    assert MercadonaMatcherService._CACHED_ONLINE_POOL is None

