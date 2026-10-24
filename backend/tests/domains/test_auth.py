import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    # 0. Registration without or with invalid token fails
    bad_token_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "carlos@ejemplo.com",
            "password": "PasswordSegura123!",
            "full_name": "Carlos Pérez",
            "registration_token": "INVALID-TOKEN-999",
        },
    )
    assert bad_token_res.status_code == 403

    # 1. Register User with valid registration token
    reg_payload = {
        "email": "carlos@ejemplo.com",
        "password": "PasswordSegura123!",
        "full_name": "Carlos Pérez",
        "registration_token": "TEST-TOKEN-1234",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "carlos@ejemplo.com"
    assert data["user"]["full_name"] == "Carlos Pérez"

    token = data["access_token"]
    refresh_token = data["refresh_token"]

    # 2. Get Profile with Bearer Token
    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "carlos@ejemplo.com"

    # 3. Duplicate Registration fails
    dup_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 409

    # 4. Login with Correct Password
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "carlos@ejemplo.com", "password": "PasswordSegura123!"},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # 5. Login with Wrong Password fails
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "carlos@ejemplo.com", "password": "WrongPassword"},
    )
    assert bad_login.status_code == 401

    # 6. Refresh Token works
    ref_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    assert "access_token" in ref_res.json()

