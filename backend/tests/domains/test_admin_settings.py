import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.domains.admin.services import AdminService
from app.domains.auth.models import User
from app.domains.integrations.client import GoogleOAuthClient


@pytest.mark.asyncio
async def test_admin_settings_oauth_and_redirect_uri(client: AsyncClient, db_session: AsyncSession):
    """Verifies that superadmin can configure Google OAuth credentials and server URL with dynamic redirect URI."""
    # 1. Register superadmin user matching SUPERADMIN_EMAIL
    reg_res = await client.post("/api/v1/auth/register", json={
        "email": settings.SUPERADMIN_EMAIL,
        "password": "SuperDatoAdmin2026!",
        "full_name": "Root Admin",
        "registration_token": "TEST-TOKEN-1234",
    })
    assert reg_res.status_code == 201
    assert reg_res.json()["user"]["is_superuser"] is True
    admin_token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Get default settings
    get_res = await client.get("/api/v1/admin/settings", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["server_public_url"] == settings.SERVER_PUBLIC_URL.rstrip("/")
    assert data["google_redirect_uri"] == f"{settings.SERVER_PUBLIC_URL.rstrip('/')}/integrations/google/callback"

    # 3. Update settings via PATCH
    patch_res = await client.patch("/api/v1/admin/settings", json={
        "server_public_url": "https://superdato.example.com",
        "google_client_id": "999888777-test.apps.googleusercontent.com",
        "google_client_secret": "GOCSPX-SecretPrueba123456",
    }, headers=headers)
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["server_public_url"] == "https://superdato.example.com"
    assert updated["google_client_id"] == "999888777-test.apps.googleusercontent.com"
    assert updated["google_client_secret_set"] is True
    assert updated["google_client_secret_masked"].startswith("••••")
    assert updated["google_redirect_uri"] == "https://superdato.example.com/integrations/google/callback"

    # 4. Verify effective google config dynamically loaded
    client_id, client_secret, redirect_uri = await AdminService.get_effective_google_config(db_session)
    assert client_id == "999888777-test.apps.googleusercontent.com"
    assert client_secret == "GOCSPX-SecretPrueba123456"
    assert redirect_uri == "https://superdato.example.com/integrations/google/callback"

    # 5. Verify Google authorization URL uses the dynamic values
    auth_url = GoogleOAuthClient.get_authorization_url(
        user_id="user-123",
        household_id="hh-123",
        client_id=client_id,
        redirect_uri=redirect_uri,
    )
    assert "client_id=999888777-test.apps.googleusercontent.com" in auth_url
    assert "redirect_uri=https%3A%2F%2Fsuperdato.example.com%2Fintegrations%2Fgoogle%2Fcallback" in auth_url

