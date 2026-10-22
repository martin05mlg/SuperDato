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

