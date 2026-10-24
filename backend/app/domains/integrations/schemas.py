import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr


class GoogleAuthUrlResponse(BaseModel):
    authorization_url: str


class GoogleConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    household_id: uuid.UUID
    google_email: str
    scopes: List[str]
    initial_sync_date: date
    last_sync_at: Optional[datetime] = None
    sync_status: str
    last_error: Optional[str] = None
    created_at: datetime


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    connection_id: Optional[uuid.UUID] = None
    source_type: str
    status: str
    messages_found: int
    receipts_imported: int
    receipts_skipped: int
    errors_count: int
    error_details: List[Dict[str, Any]] = []
    started_at: datetime
    completed_at: Optional[datetime] = None


class TriggerSyncRequest(BaseModel):
    household_id: Optional[uuid.UUID] = None

