import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domains.auth.models import User
from app.domains.catalog.models import Category, Product


@pytest.mark.asyncio
async def test_shopping_list_full_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 1. Create User
    email = f"shopper_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "StrongPassword123!"
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password(pwd),
        full_name="Shopper Tester",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()

    # Login
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Household
    hh_res = await client.post(
        "/api/v1/households",
        headers=headers,
        json={"name": "Hogar Compra Test", "currency": "EUR"},
    )
    assert hh_res.status_code == 201
    hh_id = hh_res.json()["id"]

    # 3. Add Item to Shopping List
    item_payload = {
        "household_id": hh_id,
        "name": "Leche Entera Hacendado",
        "quantity": 2.0,
        "unit_of_measure": "ud",
        "estimated_unit_price": 0.95,
        "notes": "Comprar 2 bricks",
    }
    add_res = await client.post("/api/v1/shopping/items", headers=headers, json=item_payload)
    assert add_res.status_code == 201, add_res.text
    item_data = add_res.json()
    assert item_data["name"] == "Leche Entera Hacendado"
    assert item_data["quantity"] == 2.0
    assert item_data["estimated_total"] == 1.90
    assert item_data["is_checked"] is False
    item_id = item_data["id"]

    # 4. Get List Summary
    list_res = await client.get(f"/api/v1/shopping/items?household_id={hh_id}", headers=headers)
    assert list_res.status_code == 200
    summary = list_res.json()
    assert summary["total_count"] == 1
    assert summary["pending_count"] == 1
    assert summary["checked_count"] == 0
    assert summary["estimated_total_cost"] == 1.90

    # 5. Check item off (Supermarket Mode)
    check_res = await client.patch(
        f"/api/v1/shopping/items/{item_id}?household_id={hh_id}",
        headers=headers,
        json={"is_checked": True},
    )
    assert check_res.status_code == 200
    assert check_res.json()["is_checked"] is True

    # 6. Verify summary updated
    list_res2 = await client.get(f"/api/v1/shopping/items?household_id={hh_id}", headers=headers)
    summary2 = list_res2.json()
    assert summary2["checked_count"] == 1
    assert summary2["pending_count"] == 0
    assert summary2["estimated_checked_cost"] == 1.90

    # 7. Clear checked items
    clear_res = await client.post(f"/api/v1/shopping/clear-checked?household_id={hh_id}", headers=headers)
    assert clear_res.status_code == 200
    assert clear_res.json()["cleared_count"] == 1

    # 8. List is now empty
    list_res3 = await client.get(f"/api/v1/shopping/items?household_id={hh_id}", headers=headers)
    assert list_res3.json()["total_count"] == 0

