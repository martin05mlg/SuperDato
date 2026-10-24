import re
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.password_policy import MIN_PASSWORD_LENGTH, validate_password_strength


def _validate_email_str(value: str) -> str:
    cleaned = value.strip().lower()
    # Permite dominios públicos (usuario@dominio.com), intranets (usuario@servidor.local) y localhost
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned) and not re.match(r"^[^@\s]+@localhost$", cleaned):
        raise ValueError("Introduce un correo electrónico válido (ej: admin@midominio.com).")
    return cleaned


class SetupStatusResponse(BaseModel):
    needs_setup: bool
    app_name: str


class InitialAdminSetupRequest(BaseModel):
    email: str = Field(..., description="Correo electrónico del superadministrador")
    full_name: str = Field(..., min_length=2, max_length=150)
    password: str = Field(
        ...,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=128,
        description=f"Contraseña de al menos {MIN_PASSWORD_LENGTH} caracteres",
    )

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _validate_email_str(v)

    @model_validator(mode="after")
    def check_password_policy(self) -> "InitialAdminSetupRequest":
        validate_password_strength(self.password, str(self.email))
        return self


class UserRegister(BaseModel):
    email: str = Field(..., description="Correo electrónico")
    password: str = Field(
        ...,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=128,
        description=f"Contraseña de al menos {MIN_PASSWORD_LENGTH} caracteres",
    )
    full_name: str = Field(..., min_length=2, max_length=150)
    registration_token: str = Field(..., min_length=3, description="Token seguro de invitación del superadministrador")

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _validate_email_str(v)

    @model_validator(mode="after")
    def check_password_policy(self) -> "UserRegister":
        validate_password_strength(self.password, str(self.email))
        return self


class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _validate_email_str(v)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    is_superuser: bool = False
    must_change_password: bool = False
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefresh(BaseModel):
    """Cuerpo opcional: el navegador usa la cookie HttpOnly; clientes API pueden enviar el token."""
    refresh_token: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    current_password: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=MIN_PASSWORD_LENGTH, max_length=128)

    @field_validator("password")
    @classmethod
    def check_password_policy(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            validate_password_strength(value)
        return value


class AccountDeleteRequest(BaseModel):
    password: Optional[str] = None
    current_password: Optional[str] = None

    @property
    def effective_password(self) -> str:
        return self.current_password or self.password or ""


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
