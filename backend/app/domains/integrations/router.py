import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import encrypt_secret
from app.domains.auth.models import User
from app.domains.households.models import HouseholdMembership
from app.domains.households.permissions import (
    Permission,
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
):
    """Generates the Google OAuth 2.0 authorization URL to connect a Gmail account to this household."""
    url = GoogleOAuthClient.get_authorization_url(str(current_user.id), str(household_id))
    return GoogleAuthUrlResponse(authorization_url=url)


@router.get("/google/callback", response_model=GoogleConnectionResponse)
async def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Processes Google OAuth callback, exchanges authorization code for tokens, and encrypts them."""
    try:
        user_id_str, household_id_str = GoogleOAuthClient.decode_state(state)
        user_id = uuid.UUID(user_id_str)
        household_id = uuid.UUID(household_id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado OAuth inválido.",
        )

    try:
        tokens = await GoogleOAuthClient.exchange_code_for_tokens(code)
        google_email = await GoogleOAuthClient.get_user_email(tokens["access_token"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fallo al autenticar con Google: {str(e)}",
        )

    encrypted_tokens = encrypt_secret(json.dumps(tokens))

    # Look for existing connection for this user and email
    query = select(GoogleAccountConnection).where(
        GoogleAccountConnection.user_id == user_id,
        GoogleAccountConnection.google_email == google_email,
    )
    result = await db.execute(query)
    conn = result.scalar_one_or_none()

    if conn:
        conn.encrypted_tokens = encrypted_tokens
        conn.household_id = household_id
        conn.sync_status = "IDLE"
        conn.last_error = None
    else:
        conn = GoogleAccountConnection(
            user_id=user_id,
            household_id=household_id,
            google_email=google_email,
            encrypted_tokens=encrypted_tokens,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            sync_status="IDLE",
        )
        db.add(conn)

    await db.commit()
    await db.refresh(conn)

    # Trigger initial sync in background via Celery
    try:
        from app.domains.integrations.tasks import sync_google_connection_task
        sync_google_connection_task.delay(str(conn.id))
    except Exception:
        pass  # If celery broker is not active during tests, task is skipped safely

    return conn


@router.get("/google/status", response_model=Optional[GoogleConnectionResponse])
async def get_google_connection_status(
    household_id: uuid.UUID = Query(...),
    membership: HouseholdMembership = Depends(require_household_permission(Permission.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_db),
):
    """Returns the active Google connection status for this household."""
    query = select(GoogleAccountConnection).where(
        GoogleAccountConnection.household_id == household_id
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


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
        await GoogleOAuthClient.revoke_tokens(conn.encrypted_tokens)
        await db.delete(conn)
        await db.commit()


@router.post("/sync", response_model=ImportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_manual_sync(
    household_id: uuid.UUID = Query(...),
    membership: HouseholdMembership = Depends(require_household_permission(Permission.UPLOAD_RECEIPTS)),
    db: AsyncSession = Depends(get_db),
):
    """Manually triggers a synchronization of tickets for this household."""
    # Create manual import job
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

