import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_households_multi_tenant_isolation(client: AsyncClient):
    # 1. Register User A
    user_a_res = await client.post("/api/v1/auth/register", json={
        "email": "ana@ejemplo.com",
        "password": "PasswordAna123!",
        "full_name": "Ana García",
    })
    assert user_a_res.status_code == 201
    token_a = user_a_res.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    user_b_res = await client.post("/api/v1/auth/register", json={
        "email": "borja@ejemplo.com",
        "password": "PasswordBorja123!",
        "full_name": "Borja López",
    })
    assert user_b_res.status_code == 201
    token_b = user_b_res.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A lists their households (should have initial default household)
    list_a_res = await client.get("/api/v1/households", headers=headers_a)
    assert list_a_res.status_code == 200
    households_a = list_a_res.json()
    assert len(households_a) == 1
    household_a_id = households_a[0]["id"]
    assert households_a[0]["role"] == "OWNER"

    # 4. User B lists their households (should NOT see User A's household)
    list_b_res = await client.get("/api/v1/households", headers=headers_b)
    assert list_b_res.status_code == 200
    households_b = list_b_res.json()
    assert len(households_b) == 1
    household_b_id = households_b[0]["id"]
    assert household_b_id != household_a_id

    # 5. SECURITY CHECK: User B attempts to access User A's household directly -> HTTP 403 Forbidden
    unauth_access = await client.get(f"/api/v1/households/{household_a_id}", headers=headers_b)
    assert unauth_access.status_code == 403
    assert "No perteneces a este hogar" in unauth_access.json()["detail"]

    # 6. User A creates a second shared household
    new_h_res = await client.post("/api/v1/households", json={
        "name": "Piso Compartido",
        "currency": "EUR",
    }, headers=headers_a)
    assert new_h_res.status_code == 201
    shared_h_id = new_h_res.json()["id"]

    # 7. User A invites User B to the shared household
    inv_res = await client.post(f"/api/v1/households/{shared_h_id}/invitations", json={
        "invited_email": "borja@ejemplo.com",
        "role": "MEMBER",
    }, headers=headers_a)
    assert inv_res.status_code == 201
    invitation_token = inv_res.json()["invitation_token"]
    assert invitation_token is not None

    # 8. User B accepts the invitation
    accept_res = await client.post(
        f"/api/v1/households/invitations/{invitation_token}/accept",
        headers=headers_b,
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["role"] == "MEMBER"

    # 9. Now User B can view the shared household
    view_shared = await client.get(f"/api/v1/households/{shared_h_id}", headers=headers_b)
    assert view_shared.status_code == 200
    assert view_shared.json()["role"] == "MEMBER"

    # 10. RBAC CHECK: Member cannot update household settings -> HTTP 403
    forbidden_update = await client.patch(f"/api/v1/households/{shared_h_id}", json={
        "name": "Nombre No Autorizado",
    }, headers=headers_b)
    assert forbidden_update.status_code == 403

