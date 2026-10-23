import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domains.auth.models import User
from app.domains.households.models import Household, HouseholdMembership
from app.domains.households.permissions import Role
from app.domains.catalog.models import Product, PriceObservation
from app.domains.receipts.models import Receipt


@pytest.mark.asyncio
async def test_create_manual_receipt_end_to_end(client: AsyncClient, db_session: AsyncSession):
    # 1. Register and login a test user
    email = f"manual_user_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "StrongPassword123!"

    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd, "full_name": "Manual Tester", "registration_token": None},
    )
    # Registration might need token if enabled, or check if successful
    if reg_res.status_code != 201:
        # Create user directly in db
        from app.core.security import hash_password
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hash_password(pwd),
            full_name="Manual Tester",
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        await db_session.commit()
    
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get or create household for user
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    user_id = uuid.UUID(me_res.json()["id"])

    # Create household
    hh_res = await client.post(
        "/api/v1/households",
        headers=headers,
        json={"name": "Hogar Manual Test", "currency": "EUR"},
    )
    assert hh_res.status_code == 201
    hh_id = hh_res.json()["id"]

    # 3. Create manual receipt with 2 lines
    manual_payload = {
        "household_id": hh_id,
        "purchase_datetime": "2026-10-23T11:30:00",
        "store_address": "Av. Valencia 45",
        "store_city": "Zaragoza",
        "store_postal_code": "50005",
        "payment_method": "EFECTIVO",
        "invoice_number": "TICKET-MANUAL-001",
        "lines": [
            {
                "raw_description": "LECHE ENTERA HACENDADO",
                "quantity": 3.0,
                "unit_of_measure": "ud",
                "unit_price": 0.95,
                "discount_amount": 0.0,
                "tax_rate_percent": 4.0,
                "is_weighed_item": False,
            },
            {
                "raw_description": "PLATANOS DE CANARIAS",
                "quantity": 1.5,
                "unit_of_measure": "kg",
                "unit_price": 1.99,
                "discount_amount": 0.0,
                "tax_rate_percent": 4.0,
                "is_weighed_item": True,
                "weight_in_kg": 1.5,
            },
        ],
    }

    create_res = await client.post("/api/v1/receipts/manual", headers=headers, json=manual_payload)
    assert create_res.status_code == 201, create_res.text
    data = create_res.json()

    assert data["invoice_number"] == "TICKET-MANUAL-001"
    assert data["household_id"] == hh_id
    assert data["payment_method"] == "EFECTIVO"
    assert data["lines_count"] == 2
    # 3 * 0.95 = 2.85, 1.5 * 1.99 = 2.985 (rounds to 2.98). Total = 5.83
    assert round(data["total_amount"], 2) == 5.83
    assert len(data["lines"]) == 2
    assert len(data["tax_lines"]) == 1
    assert data["tax_lines"][0]["tax_rate_percent"] == 4.0

    # 4. Verify catalog product was created/linked and price observation registered
    stmt = select(PriceObservation).where(PriceObservation.household_id == uuid.UUID(hh_id))
    obs_res = await db_session.execute(stmt)
    observations = obs_res.scalars().all()
    assert len(observations) == 2
