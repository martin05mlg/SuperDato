import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import encrypt_secret
from app.domains.auth.models import User
from app.domains.households.models import HouseholdMembership
from app.domains.households.permissions import (
    Permission,
    Role,
    ROLE_PERMISSIONS,
    get_current_user,
    require_household_permission,
)
from app.domains.integrations.client import GoogleOAuthClient
from app.domains.integrations.models import GoogleAccountConnection, ImportJob
from app.domains.integrations.schemas import (
    GoogleAuthUrlResponse,
    GoogleConnectionResponse,
    ImportJobResponse,
    TriggerSyncRequest,
)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get("/google/authorize-url", response_model=GoogleAuthUrlResponse)
async def get_google_authorize_url(
    household_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    membership: HouseholdMembership = Depends(require_household_permission(Permission.CONNECT_INTEGRATIONS)),
    db: AsyncSession = Depends(get_db),
):
    """Generates the Google OAuth 2.0 authorization URL to connect a Gmail account to this household."""
    from app.domains.admin.services import AdminService

    client_id, _, redirect_uri = await AdminService.get_effective_google_config(db)
    url = GoogleOAuthClient.get_authorization_url(
        str(current_user.id),
        str(household_id),
        client_id=client_id,
        redirect_uri=redirect_uri,
    )
    return GoogleAuthUrlResponse(authorization_url=url)


@router.get("/google/callback", response_model=GoogleConnectionResponse)
async def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Processes Google OAuth callback, verifies signed state and user permissions, exchanges code for tokens, and encrypts them."""
    try:
        user_id_str, household_id_str = GoogleOAuthClient.decode_state(state)
        user_id = uuid.UUID(user_id_str)
        household_id = uuid.UUID(household_id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado OAuth inválido, expirado o manipulado.",
        )

    if not current_user.is_superuser and user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El estado de autorización OAuth no corresponde al usuario autenticado.",
        )

    if not current_user.is_superuser:
        mem_res = await db.execute(
            select(HouseholdMembership).where(
                HouseholdMembership.household_id == household_id,
                HouseholdMembership.user_id == current_user.id,
            )
        )
        membership = mem_res.scalar_one_or_none()
        if not membership or Permission.CONNECT_INTEGRATIONS not in ROLE_PERMISSIONS.get(Role(membership.role), set()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos en este hogar para vincular integraciones de Google.",
            )

    from app.domains.admin.services import AdminService
    client_id, client_secret, redirect_uri = await AdminService.get_effective_google_config(db)

    try:
        tokens = await GoogleOAuthClient.exchange_code_for_tokens(
            code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
        google_email = await GoogleOAuthClient.get_user_email(tokens["access_token"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al intercambiar código con Google: {str(e)}",
        )

    encrypted_payload = encrypt_secret(json.dumps(tokens))

    # Check if connection already exists
    query = select(GoogleAccountConnection).where(
        GoogleAccountConnection.household_id == household_id
    )
    result = await db.execute(query)
    conn = result.scalar_one_or_none()

    if not conn:
        conn = GoogleAccountConnection(
            id=uuid.uuid4(),
            user_id=user_id,
            household_id=household_id,
            google_email=google_email,
            encrypted_tokens=encrypted_payload,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            initial_sync_date=datetime.now(timezone.utc).date(),
            sync_status="IDLE",
        )
        db.add(conn)
    else:
        conn.google_email = google_email
        conn.encrypted_tokens = encrypted_payload
        conn.sync_status = "IDLE"
        conn.last_error = None

    await db.commit()
    await db.refresh(conn)
    return conn


@router.get("/google/status", response_model=Optional[GoogleConnectionResponse])
async def get_google_connection_status(
    household_id: uuid.UUID = Query(...),
    membership: HouseholdMembership = Depends(require_household_permission(Permission.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_db),
):
    """Returns the current connection status of Gmail for this household."""
    query = select(GoogleAccountConnection).where(
        GoogleAccountConnection.household_id == household_id
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


@router.post("/google/connect-mock", response_model=GoogleConnectionResponse)
async def connect_mock_google_account(
    household_id: uuid.UUID = Query(...),
    email: str = Query("mi.cuenta.mercadona@gmail.com"),
    current_user: User = Depends(get_current_user),
    membership: HouseholdMembership = Depends(require_household_permission(Permission.CONNECT_INTEGRATIONS)),
    db: AsyncSession = Depends(get_db),
):
    """Simulates connecting a Google account for local testing without requiring external Google Cloud API keys."""
    if settings.ENVIRONMENT.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El endpoint de simulación OAuth está deshabilitado en producción.",
        )

    stmt = select(GoogleAccountConnection).where(GoogleAccountConnection.household_id == household_id)
    res = await db.execute(stmt)
    conn = res.scalar_one_or_none()

    mock_tokens = json.dumps({"access_token": "mock_token", "refresh_token": "mock_refresh", "expires_in": 3600})
    encrypted = encrypt_secret(mock_tokens)

    if not conn:
        conn = GoogleAccountConnection(
            id=uuid.uuid4(),
            user_id=current_user.id,
            household_id=household_id,
            google_email=email,
            encrypted_tokens=encrypted,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            initial_sync_date=datetime.now(timezone.utc).date(),
            sync_status="IDLE",
        )
        db.add(conn)
    else:
        conn.google_email = email
        conn.sync_status = "IDLE"
        conn.last_error = None

    await db.commit()
    await db.refresh(conn)
    return conn


@router.post("/google/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_google_account(
    household_id: uuid.UUID = Query(...),
    membership: HouseholdMembership = Depends(require_household_permission(Permission.CONNECT_INTEGRATIONS)),
    db: AsyncSession = Depends(get_db),
):
    """Revokes tokens with Google and disconnects the account from this household."""
    query = select(GoogleAccountConnection).where(
        GoogleAccountConnection.household_id == household_id
    )
    result = await db.execute(query)
    conn = result.scalar_one_or_none()

    if conn:
        try:
            await GoogleOAuthClient.revoke_tokens(conn.encrypted_tokens)
        except Exception:
            pass
        await db.delete(conn)
        await db.commit()


@router.post("/sync", response_model=ImportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_manual_sync(
    household_id: uuid.UUID = Query(...),
    membership: HouseholdMembership = Depends(require_household_permission(Permission.UPLOAD_RECEIPTS)),
    db: AsyncSession = Depends(get_db),
):
    """Manually triggers a synchronization of tickets from connected Gmail account or fallback."""
    query = select(GoogleAccountConnection).where(
        GoogleAccountConnection.household_id == household_id
    )
    res = await db.execute(query)
    conn = res.scalar_one_or_none()

    if conn:
        from app.domains.integrations.tasks import _async_sync_connection
        sync_result = await _async_sync_connection(str(conn.id))
        job_id = uuid.UUID(sync_result["job_id"])
        job = await db.get(ImportJob, job_id)
        if job:
            return job

    if settings.ENVIRONMENT.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay ninguna cuenta de Gmail conectada a este hogar.",
        )

    # Fallback when no Google account is connected (development/testing only)
    job = ImportJob(
        household_id=household_id,
        source_type="GMAIL_MANUAL",
        status="COMPLETED",
        messages_found=2,
        receipts_imported=2,
        receipts_skipped=0,
        errors_count=0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/imports", response_model=List[ImportJobResponse])
async def list_import_jobs(
    household_id: uuid.UUID = Query(...),
    membership: HouseholdMembership = Depends(require_household_permission(Permission.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_db),
):
    """Returns the history of import jobs for this household."""
    query = (
        select(ImportJob)
        .where(ImportJob.household_id == household_id)
        .order_by(ImportJob.started_at.desc())
    )
    result = await db.execute(query)
    jobs = result.scalars().all()
    return jobs
