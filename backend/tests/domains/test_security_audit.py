import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.receipts.services import ReceiptService


@pytest.mark.asyncio
async def test_unauthenticated_requests_are_rejected(client: AsyncClient):
    """
    CRITICAL SECURITY TEST:
    Verifies that requests without valid credentials receive HTTP 401 Unauthorized,
    preventing any fallback to a default dev superuser.
    """
    # 1. Receipts endpoints
    res = await client.get("/api/v1/receipts")
    assert res.status_code == 401
    assert "Autenticación requerida" in res.json()["detail"]

    random_id = str(uuid.uuid4())
    res = await client.get(f"/api/v1/receipts/{random_id}")
    assert res.status_code == 401

    res = await client.patch(f"/api/v1/receipts/{random_id}", json={"store_city": "Madrid"})
    assert res.status_code == 401

    res = await client.patch(f"/api/v1/receipts/{random_id}/lines/{random_id}", json={"unit_price": 2.5})
    assert res.status_code == 401

    # 2. Analytics endpoints
    res = await client.get("/api/v1/analytics/summary")
    assert res.status_code == 401

    res = await client.get("/api/v1/analytics/category-distribution")
    assert res.status_code == 401

    # 3. Households endpoints
    res = await client.get("/api/v1/households")
    assert res.status_code == 401

    # 4. Catalog endpoints
    res = await client.get("/api/v1/catalog/products")
    assert res.status_code == 401

    res = await client.get("/api/v1/catalog/categories")
    assert res.status_code == 401

    # 5. Superadmin endpoints
    res = await client.get("/api/v1/admin/stats")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_idor_cross_household_receipt_access_prevented(client: AsyncClient, db_session: AsyncSession):
    """
    CRITICAL SECURITY TEST:
    Verifies that User B cannot read or alter receipts belonging to User A's household (IDOR).
    """
    # 1. Register User A
    user_a_res = await client.post("/api/v1/auth/register", json={
        "email": "owner_a@ejemplo.com",
        "password": "PasswordA123!",
        "full_name": "Propietario A",
        "registration_token": "TEST-TOKEN-1234",
    })
    assert user_a_res.status_code == 201
    token_a = user_a_res.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B (Attacker)
    user_b_res = await client.post("/api/v1/auth/register", json={
        "email": "attacker_b@ejemplo.com",
        "password": "PasswordB123!",
        "full_name": "Atacante B",
        "registration_token": "TEST-TOKEN-1234",
    })
    assert user_b_res.status_code == 201
    token_b = user_b_res.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Get User A's household
    households_a = (await client.get("/api/v1/households", headers=headers_a)).json()
    household_a_id = uuid.UUID(households_a[0]["id"])

    # User A uploads / seeds a receipt
    await ReceiptService.sync_sample_receipts_to_db(db_session)
    receipts_a = (await client.get("/api/v1/receipts", headers=headers_a)).json()
    assert len(receipts_a) > 0
    victim_receipt_id = receipts_a[0]["id"]

    # Assign to Household A
    await ReceiptService.assign_household(
        db_session,
        victim_receipt_id,
        household_a_id,
        uuid.UUID(user_a_res.json()["user"]["id"]),
    )

    # 3. IDOR CHECK: User B attempts to GET victim receipt detail -> 403 Forbidden
    idor_read = await client.get(f"/api/v1/receipts/{victim_receipt_id}", headers=headers_b)
    assert idor_read.status_code == 403
    assert "No perteneces al hogar" in idor_read.json()["detail"]

    # 4. IDOR CHECK: User B attempts to PATCH victim receipt -> 403 Forbidden
    idor_update = await client.patch(
        f"/api/v1/receipts/{victim_receipt_id}",
        json={"store_city": "Hacked City"},
        headers=headers_b,
    )
    assert idor_update.status_code == 403

    # 5. IDOR CHECK: User B attempts to PATCH a line on victim receipt -> 403 Forbidden
    victim_detail = (await client.get(f"/api/v1/receipts/{victim_receipt_id}", headers=headers_a)).json()
    line_id = victim_detail["lines"][0]["id"]

    idor_line_update = await client.patch(
        f"/api/v1/receipts/{victim_receipt_id}/lines/{line_id}",
        json={"unit_price": 999.99},
        headers=headers_b,
    )
    assert idor_line_update.status_code == 403

    # 6. IDOR CHECK: User B attempts to view User A's analytics -> 403 Forbidden
    idor_analytics = await client.get(
        f"/api/v1/analytics/summary?household_id={household_a_id}",
        headers=headers_b,
    )
    assert idor_analytics.status_code == 403

    # 7. IDOR CHECK: User B attempts to view User A's product catalog -> 403 Forbidden
    idor_catalog = await client.get(
        f"/api/v1/catalog/products?household_id={household_a_id}",
        headers=headers_b,
    )
    assert idor_catalog.status_code == 403


@pytest.mark.asyncio
async def test_pdf_upload_security_limits(auth_client: AsyncClient):
    """
    CRITICAL SECURITY TEST:
    Verifies that receipt upload rejects oversize files (DoS prevention),
    rejects invalid file types/headers, and sanitizes exception leakage.
    """
    # 1. Reject non-PDF file extension
    txt_file = io.BytesIO(b"Hello text file")
    res_txt = await auth_client.post(
        "/api/v1/receipts/upload",
        files={"file": ("ticket.txt", txt_file, "text/plain")},
    )
    assert res_txt.status_code == 400
    assert "Solo se admiten archivos en formato PDF" in res_txt.json()["detail"]

    # 2. Reject fake PDF without %PDF- magic header
    fake_pdf = io.BytesIO(b"NOT A REAL PDF CONTENT HERE")
    res_fake = await auth_client.post(
        "/api/v1/receipts/upload",
        files={"file": ("ticket.pdf", fake_pdf, "application/pdf")},
    )
    assert res_fake.status_code == 400
    assert "no es un documento PDF válido" in res_fake.json()["detail"]

    # 3. Reject oversized file > 10 MB (DoS protection)
    # Generate 11 MB of dummy bytes starting with %PDF-
    large_pdf_bytes = b"%PDF-" + b"0" * (11 * 1024 * 1024)
    large_pdf = io.BytesIO(large_pdf_bytes)
    res_large = await auth_client.post(
        "/api/v1/receipts/upload",
        files={"file": ("large_exploit.pdf", large_pdf, "application/pdf")},
    )
    assert res_large.status_code == 413
    assert "tamaño máximo permitido (10 MB)" in res_large.json()["detail"]

    # 4. Error message sanitization on corrupted PDF
    # Starts with %PDF- so passes header check, but contains garbage parser cannot parse
    corrupt_pdf = io.BytesIO(b"%PDF-1.4\nCorrupted garbage data that causes parsing error")
    res_corrupt = await auth_client.post(
        "/api/v1/receipts/upload",
        files={"file": ("corrupt.pdf", corrupt_pdf, "application/pdf")},
    )
    assert res_corrupt.status_code == 422
    # Verify that raw Python traceback or internal SQLite error strings are NOT leaked in detail
    detail = res_corrupt.json()["detail"]
    assert "Traceback" not in detail
    assert "sqlite" not in detail.lower()
    assert "No se pudo procesar el ticket PDF" in detail

