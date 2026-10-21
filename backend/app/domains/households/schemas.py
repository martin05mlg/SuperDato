import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class HouseholdCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    currency: str = Field("EUR", min_length=3, max_length=3)


class HouseholdUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)


class HouseholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    currency: str
    role: str
    created_at: datetime


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    user_name: str
    role: str
    joined_at: datetime


class MemberRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(ADMIN|MEMBER)$")


class InvitationCreate(BaseModel):
    invited_email: EmailStr
    role: str = Field("MEMBER", pattern="^(ADMIN|MEMBER)$")


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    invited_email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime
    invitation_token: Optional[str] = None

