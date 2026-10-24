import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Contraseña de al menos 8 caracteres")
    full_name: str = Field(..., min_length=2, max_length=150)
    registration_token: str = Field(..., min_length=3, description="Token seguro de invitación del superadministrador")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_verified: bool
    is_superuser: bool = False
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefresh(BaseModel):
    refresh_token: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    current_password: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)


class RegistrationTokenCreate(BaseModel):
    token: Optional[str] = None
    note: Optional[str] = None
    max_uses: int = Field(default=1, ge=1, le=1000)
    expires_in_days: Optional[int] = Field(default=30, ge=1, le=365)


class RegistrationTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    token: str
    note: Optional[str] = None
    max_uses: int
    times_used: int
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime

