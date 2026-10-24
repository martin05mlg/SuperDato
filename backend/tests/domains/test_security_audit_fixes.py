import base64
import json
import uuid
from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.security import create_access_token, hash_password
from app.domains.auth.models import User
from app.domains.catalog.models import Product
from app.domains.catalog.services import CatalogService
from app.domains.households.models import Household, HouseholdMembership
from app.domains.integrations.client import GoogleOAuthClient


@pytest.mark.asyncio
async def test_vuln01_oauth_state_tampering_and_callback_auth(client: AsyncClient):
    """VULN-01: Forged Base64 OAuth state is rejected and callback requires authenticated owner/admin."""
    # 1. Forged plain Base64 state must be rejected by decode_state
    forged_raw = base64.urlsafe_b64encode(
        json.dumps({"u": str(uuid.uuid4()), "h": str(uuid.uuid4()), "t": 9999999999}).encode()
    ).decode()
    with pytest.raises(ValueError):
        GoogleOAuthClient.decode_state(forged_raw)

    # 2. Unauthenticated call to /integrations/google/callback must return 401
    unauth_res = await client.get(
        f"/api/v1/integrations/google/callback?code=fake_code&state={forged_raw}"
    )
    assert unauth_res.status_code == 401

    # 3. Authenticated user B cannot use state generated for user A
    u1_res = await client.post("/api/v1/auth/register", json={
        "email": "user_a_oauth@ejemplo.com",
        "password": "PasswordSegura123!",
        "full_name": "User A",
        "registration_token": "TEST-TOKEN-1234",
    })
    u1_id = u1_res.json()["user"]["id"]
    u1_headers = {"Authorization": f"Bearer {u1_res.json()['access_token']}"}
    h1_res = await client.get("/api/v1/households", headers=u1_headers)
    h1_id = h1_res.json()[0]["id"]

    # Valid signed state for User A
    url_a = GoogleOAuthClient.get_authorization_url(u1_id, h1_id)
    import urllib.parse
    state_a = urllib.parse.parse_qs(urllib.parse.urlparse(url_a).query)["state"][0]

    # Register User B
    u2_res = await client.post("/api/v1/auth/register", json={
        "email": "user_b_oauth@ejemplo.com",
        "password": "PasswordSegura123!",
        "full_name": "User B",
        "registration_token": "TEST-TOKEN-1234",
    })
    u2_headers = {"Authorization": f"Bearer {u2_res.json()['access_token']}"}

    # User B tries to invoke callback with User A's state -> 403 Forbidden
    hijack_res = await client.get(
        f"/api/v1/integrations/google/callback?code=fake_code&state={state_a}",
        headers=u2_headers,
    )
    assert hijack_res.status_code == 403


@pytest.mark.asyncio
async def test_vuln02_cors_restricts_external_origins(client: AsyncClient):
    """VULN-02: Arbitrary external websites are not reflected in Access-Control-Allow-Origin."""
    # External malicious origin
    bad_cors = await client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "https://evil-attacker-domain.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert bad_cors.headers.get("access-control-allow-origin") != "https://evil-attacker-domain.com"

    # Authorized LAN IP origin
    good_cors = await client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://10.15.15.100:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert good_cors.headers.get("access-control-allow-origin") == "http://10.15.15.100:5173"


@pytest.mark.asyncio
async def test_vuln03_brute_force_account_lockout(client: AsyncClient):
    """VULN-03: 5 consecutive failed login attempts lock the account with HTTP 429."""
    await client.post("/api/v1/auth/register", json={
        "email": "bruteforce@ejemplo.com",
        "password": "CorrectPassword123!",
        "full_name": "Victim User",
        "registration_token": "TEST-TOKEN-1234",
    })

    # 5 failed attempts return 401
    for _ in range(5):
        res = await client.post("/api/v1/auth/login", json={
            "email": "bruteforce@ejemplo.com",
            "password": "WrongPassword!",
        })
        assert res.status_code == 401

    # 6th attempt even with the CORRECT password must be blocked with 429 Too Many Requests
    locked_res = await client.post("/api/v1/auth/login", json={
        "email": "bruteforce@ejemplo.com",
        "password": "CorrectPassword123!",
    })
    assert locked_res.status_code == 429


@pytest.mark.asyncio
async def test_vuln04_product_detail_price_observations_isolation(
    client: AsyncClient, db_session: AsyncSession
):
    """VULN-04: GET /catalog/products/{id} must not leak price observations from other households."""
    # Household A records an observation of 88.50 €
    hh_a = Household(id=uuid.uuid4(), name="Hogar A", currency="EUR", created_by_user_id=uuid.uuid4())
    db_session.add(hh_a)
    await db_session.flush()

    prod = await CatalogService.get_or_create_product_for_line(
        db=db_session,
        raw_description="JAMON IBERICO BELLOTA",
        category_hint="Carnicería y Charcutería",
    )
    await CatalogService.record_price_observation(
        db=db_session,
        household_id=hh_a.id,
        product_id=prod.id,
        receipt_line_id=uuid.uuid4(),
        observed_at=datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc),
        observed_date=date(2026, 10, 20),
        unit_price=88.50,
    )
    await db_session.commit()

    # Register User B (belongs only to their own Household B)
    u_b = await client.post("/api/v1/auth/register", json={
        "email": "user_b_isolation@ejemplo.com",
        "password": "PasswordSegura123!",
        "full_name": "User B",
        "registration_token": "TEST-TOKEN-1234",
    })
    headers_b = {"Authorization": f"Bearer {u_b.json()['access_token']}"}

    # User B fetches product detail -> sees canonical product metadata, but 0 price observations from Household A
    prod_res = await client.get(f"/api/v1/catalog/products/{prod.id}", headers=headers_b)
    assert prod_res.status_code == 200
    data = prod_res.json()
    assert data["observations_count"] == 0
    assert data["latest_price"] is None


@pytest.mark.asyncio
async def test_vuln05_catalog_mutations_require_admin_or_owner(
    client: AsyncClient, db_session: AsyncSession
):
    """VULN-05: A user who only has MEMBER role cannot mutate global catalog or trigger sync/recategorize."""
    member_user = User(
        id=uuid.uuid4(),
        email="member_only@ejemplo.com",
        hashed_password=hash_password("MemberPass123!"),
        full_name="Basic Member",
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )
    db_session.add(member_user)
    await db_session.flush()

    hh = Household(id=uuid.uuid4(), name="Hogar Compartido", currency="EUR", created_by_user_id=uuid.uuid4())
    db_session.add(hh)
    await db_session.flush()

    db_session.add(HouseholdMembership(
        id=uuid.uuid4(),
        household_id=hh.id,
        user_id=member_user.id,
        role="MEMBER",
    ))
    await db_session.commit()

    member_token = create_access_token(subject=str(member_user.id))
    headers = {"Authorization": f"Bearer {member_token}"}

    recat_res = await client.post("/api/v1/catalog/recategorize-all", headers=headers)
    assert recat_res.status_code == 403

    reject_res = await client.post(
        "/api/v1/catalog/mercadona/reject-match",
        json={"product_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert reject_res.status_code == 403


@pytest.mark.asyncio
async def test_vuln06_mock_endpoints_disabled_in_production(client: AsyncClient, monkeypatch):
    """VULN-06: connect-mock and unlinked sync fallback are blocked when ENVIRONMENT=production."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": "prod_test@ejemplo.com",
        "password": "PasswordSegura123!",
        "full_name": "Prod User",
        "registration_token": "TEST-TOKEN-1234",
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    h_res = await client.get("/api/v1/households", headers=headers)
    hh_id = h_res.json()[0]["id"]

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    mock_res = await client.post(
        f"/api/v1/integrations/google/connect-mock?household_id={hh_id}",
        headers=headers,
    )
    assert mock_res.status_code == 403

    sync_res = await client.post(
        f"/api/v1/integrations/sync?household_id={hh_id}",
        headers=headers,
    )
    assert sync_res.status_code == 400


@pytest.mark.asyncio
async def test_vuln07_and_vuln09_password_change_requires_current_and_invalidates_tokens(client: AsyncClient):
    """VULN-07 & VULN-09: Changing password requires current_password and immediately invalidates prior tokens."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": "sec_pwd@ejemplo.com",
        "password": "OldPassword123!",
        "full_name": "Sec User",
        "registration_token": "TEST-TOKEN-1234",
    })
    old_access = reg.json()["access_token"]
    old_refresh = reg.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {old_access}"}

    # 1. Missing current_password -> 400
    no_curr_res = await client.patch(
        "/api/v1/auth/me",
        json={"password": "NewPassword456!"},
        headers=headers,
    )
    assert no_curr_res.status_code == 400

    # 2. Wrong current_password -> 401
    wrong_curr_res = await client.patch(
        "/api/v1/auth/me",
        json={"current_password": "WrongOldPassword!", "password": "NewPassword456!"},
        headers=headers,
    )
    assert wrong_curr_res.status_code == 401

    # 3. Correct current_password -> 200 OK
    ok_res = await client.patch(
        "/api/v1/auth/me",
        json={"current_password": "OldPassword123!", "password": "NewPassword456!"},
        headers=headers,
    )
    assert ok_res.status_code == 200

    # 4. Old access_token is now invalidated -> 401
    me_old = await client.get("/api/v1/auth/me", headers=headers)
    assert me_old.status_code == 401

    # 5. Old refresh_token is now invalidated -> 401
    ref_old = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert ref_old.status_code == 401


def test_vuln08_production_secrets_validation():
    """VULN-08: Starting Settings in production with default secrets raises ValidationError."""
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="insecure_dev_secret_key_change_in_production_1234567890abcdef",
        )

    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a_very_strong_custom_production_secret_key_32_bytes_plus",
            ENCRYPTION_MASTER_KEY="01234567890123456789012345678901",
        )

