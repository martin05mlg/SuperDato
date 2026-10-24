import json
import uuid
import pytest
from httpx import AsyncClient
from app.core.security import decrypt_secret, encrypt_secret
from app.domains.integrations.client import GoogleOAuthClient


@pytest.mark.asyncio
async def test_google_oauth_token_encryption():
    # Sensitive tokens payload
    raw_tokens = {
        "access_token": "ya29.sample_google_access_token_mock",
        "refresh_token": "1//04_sample_google_refresh_token_mock",
        "expires_in": 3600,
    }
    raw_json = json.dumps(raw_tokens)

    # 1. Encrypt tokens
    encrypted = encrypt_secret(raw_json)
    assert encrypted != raw_json
    assert "sample_google_refresh_token" not in encrypted

    # 2. Decrypt tokens
    decrypted = decrypt_secret(encrypted)
    assert decrypted == raw_json
    recovered = json.loads(decrypted)
    assert recovered["refresh_token"] == raw_tokens["refresh_token"]


@pytest.mark.asyncio
async def test_google_authorize_url_and_state(client: AsyncClient):
    # Register a user
    user_res = await client.post("/api/v1/auth/register", json={
        "email": "laura@ejemplo.com",
        "password": "PasswordLaura123!",
        "full_name": "Laura Sánchez",
        "registration_token": "TEST-TOKEN-1234",
    })
    token = user_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get household id
    h_res = await client.get("/api/v1/households", headers=headers)
    household_id = h_res.json()[0]["id"]

    # 1. Get Authorize URL
    auth_url_res = await client.get(
        f"/api/v1/integrations/google/authorize-url?household_id={household_id}",
        headers=headers,
    )
    assert auth_url_res.status_code == 200
    url = auth_url_res.json()["authorization_url"]
    assert "accounts.google.com" in url
    assert "client_id=" in url
    assert "state=" in url

    # 2. Extract and decode state
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    state = params["state"][0]

    user_id_out, household_id_out = GoogleOAuthClient.decode_state(state)
    assert household_id_out == household_id


@pytest.mark.asyncio
async def test_trigger_sync_and_import_jobs(client: AsyncClient):
    # Register user
    user_res = await client.post("/api/v1/auth/register", json={
        "email": "pablo@ejemplo.com",
        "password": "PasswordPablo123!",
        "full_name": "Pablo Ruiz",
        "registration_token": "TEST-TOKEN-1234",
    })
    token = user_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    h_res = await client.get("/api/v1/households", headers=headers)
    household_id = h_res.json()[0]["id"]

    # 1. Trigger manual sync
    sync_res = await client.post(
        f"/api/v1/integrations/sync?household_id={household_id}",
        headers=headers,
    )
    assert sync_res.status_code == 202
    job = sync_res.json()
    assert job["status"] == "COMPLETED"
    assert job["receipts_imported"] >= 1

    # 2. List import jobs
    jobs_res = await client.get(
        f"/api/v1/integrations/imports?household_id={household_id}",
        headers=headers,
    )
    assert jobs_res.status_code == 200
    jobs = jobs_res.json()
    assert len(jobs) >= 1
    assert jobs[0]["household_id"] == household_id


@pytest.mark.asyncio
async def test_multi_user_email_connections_in_same_household(client: AsyncClient):
    # 1. Register User 1 (Owner)
    u1_res = await client.post("/api/v1/auth/register", json={
        "email": "user1.owner@ejemplo.com",
        "password": "PasswordUser1_123!",
        "full_name": "Usuario Uno",
        "registration_token": "TEST-TOKEN-1234",
    })
    token1 = u1_res.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Get household
    hh_res = await client.get("/api/v1/households", headers=headers1)
    household_id = hh_res.json()[0]["id"]

    # 2. Register User 2
    u2_res = await client.post("/api/v1/auth/register", json={
        "email": "user2.member@ejemplo.com",
        "password": "PasswordUser2_123!",
        "full_name": "Usuario Dos",
        "registration_token": "TEST-TOKEN-1234",
    })
    token2 = u2_res.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Invite and add User 2 to household
    inv_res = await client.post(
        f"/api/v1/households/{household_id}/invitations",
        headers=headers1,
        json={"invited_email": "user2.member@ejemplo.com", "role": "MEMBER"},
    )
    assert inv_res.status_code == 201
    invitation_token = inv_res.json()["invitation_token"]

    accept_res = await client.post(
        f"/api/v1/households/invitations/{invitation_token}/accept",
        headers=headers2,
    )
    assert accept_res.status_code == 200

    # 3. User 1 connects their Gmail
    conn1_res = await client.post(
        f"/api/v1/integrations/google/connect-mock?household_id={household_id}&email=user1.personal@gmail.com",
        headers=headers1,
    )
    assert conn1_res.status_code == 200
    conn1_id = conn1_res.json()["id"]

    # 4. User 2 connects their Gmail to the same household
    conn2_res = await client.post(
        f"/api/v1/integrations/google/connect-mock?household_id={household_id}&email=user2.personal@gmail.com",
        headers=headers2,
    )
    assert conn2_res.status_code == 200
    conn2_id = conn2_res.json()["id"]

    # 5. Verify both connections are active in the household
    list_conns_res = await client.get(
        f"/api/v1/integrations/google/connections?household_id={household_id}",
        headers=headers1,
    )
    assert list_conns_res.status_code == 200
    conns = list_conns_res.json()
    assert len(conns) == 2
    emails = [c["google_email"] for c in conns]
    assert "user1.personal@gmail.com" in emails
    assert "user2.personal@gmail.com" in emails

    # 6. User 2 disconnects their connection
    del_res = await client.post(
        f"/api/v1/integrations/google/disconnect?household_id={household_id}&connection_id={conn2_id}",
        headers=headers2,
    )
    assert del_res.status_code == 204

    # 7. Verify only User 1's connection remains
    list_after_res = await client.get(
        f"/api/v1/integrations/google/connections?household_id={household_id}",
        headers=headers1,
    )
    assert list_after_res.status_code == 200
    conns_after = list_after_res.json()
    assert len(conns_after) == 1
    assert conns_after[0]["google_email"] == "user1.personal@gmail.com"


