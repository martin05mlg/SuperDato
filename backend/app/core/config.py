import json
import os
from pathlib import Path
import secrets
from typing import List, Tuple, Union
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_data_dir() -> Path:
    """Resolves directory for persistent state (e.g. auto-generated secrets)."""
    env_dir = os.getenv("SUPERDATO_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p
    # Standard container mount path
    if os.path.exists("/app"):
        p = Path("/app/data")
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass
    # Local fallback
    p = Path(__file__).resolve().parent.parent.parent / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _load_or_create_secrets() -> Tuple[str, str]:
    """
    Loads or generates persistent cryptographic secrets.
    Saves to a shared .secrets.json file in the persistent data volume
    so all containers (API, Worker, Beat) share identical keys across restarts.
    """
    data_dir = _resolve_data_dir()
    secrets_file = data_dir / ".secrets.json"

    if secrets_file.exists():
        try:
            with open(secrets_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                s_key = data.get("secret_key")
                e_key = data.get("encryption_master_key")
                if s_key and e_key:
                    return str(s_key), str(e_key)
        except Exception:
            pass

    sec_key = secrets.token_urlsafe(64)
    enc_key = secrets.token_urlsafe(32)
    payload = {
        "secret_key": sec_key,
        "encryption_master_key": enc_key,
    }
    try:
        temp_file = data_dir / f".secrets.tmp.{os.getpid()}"
        fd = os.open(temp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(temp_file, secrets_file)
        try:
            os.chmod(secrets_file, 0o600)
        except OSError:
            pass
    except Exception:
        if secrets_file.exists():
            try:
                with open(secrets_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return str(data.get("secret_key", sec_key)), str(data.get("encryption_master_key", enc_key))
            except Exception:
                pass
    return sec_key, enc_key


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # General Application
    APP_NAME: str = "SuperDato"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # CORS (el origen de SERVER_PUBLIC_URL se añade automáticamente; usa CORS_EXTRA_ORIGINS para más)
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    CORS_EXTRA_ORIGINS: List[str] = []

    # Operación y exposición
    ENABLE_DOCS: bool = False  # Swagger/OpenAPI: siempre activo fuera de producción; en producción solo si True
    RATE_LIMIT_ENABLED: bool = True
    AUTO_MIGRATE: bool = True  # Ejecuta `alembic upgrade head` al arrancar la API
    ENABLE_MERCADONA_ONLINE: bool = False  # Enriquecimiento opt-in vía tienda.mercadona.es (API no oficial)

    # Database
    # Default to local postgresql+asyncpg, or sqlite+aiosqlite for local tests without postgres
    DATABASE_URL: str = "postgresql+asyncpg://superdato:superdato@localhost:5432/superdato_db"

    @property
    def sync_database_url(self) -> str:
        """URL for sync drivers (such as Alembic or sync inspection)."""
        url = self.DATABASE_URL
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        elif url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://")
        return url

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Security & JWT
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # Master Key for Encrypting Google OAuth Tokens in Database
    # Must be 32 url-safe base64-encoded bytes or 32+ chars
    ENCRYPTION_MASTER_KEY: str = ""

    # Google OAuth 2.0 Credentials (Fallback or Initial)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/integrations/google/callback"

    # Server Public URL & Superadmin Defaults
    SERVER_PUBLIC_URL: str = "http://localhost:5173"
    SUPERADMIN_EMAIL: str = "admin@superdato.com"
    # Vacío => se genera una contraseña aleatoria en el primer arranque y se muestra UNA vez en los logs.
    SUPERADMIN_PASSWORD: str = ""

    # Data Seeding Control
    AUTO_SEED_SAMPLES: bool = True

    @model_validator(mode="after")
    def resolve_and_validate_secrets(self) -> "Settings":
        """
        Auto-generates and persists cryptographically strong secrets if omitted or empty,
        ensuring zero-configuration deployments remain completely secure across restarts.
        """
        # 1. Auto-generate persistent secrets when omitted or blank
        if not self.SECRET_KEY or not self.ENCRYPTION_MASTER_KEY:
            stored_sec, stored_enc = _load_or_create_secrets()
            if not self.SECRET_KEY:
                self.SECRET_KEY = stored_sec
            if not self.ENCRYPTION_MASTER_KEY:
                self.ENCRYPTION_MASTER_KEY = stored_enc

        # 2. Block known insecure defaults when explicitly provided in production
        if self.ENVIRONMENT.lower() == "production":
            if (
                self.SECRET_KEY.startswith("insecure_dev_secret_key")
                or len(self.SECRET_KEY) < 32
            ):
                raise ValueError(
                    "Seguridad crítica: En entorno de producción debes configurar un SECRET_KEY seguro de al menos 32 caracteres (o dejarlo vacío para auto-generación segura)."
                )
            if (
                self.ENCRYPTION_MASTER_KEY == "01234567890123456789012345678901"
                or len(self.ENCRYPTION_MASTER_KEY) < 32
            ):
                raise ValueError(
                    "Seguridad crítica: En entorno de producción debes configurar una ENCRYPTION_MASTER_KEY única de al menos 32 caracteres (o dejarlo vacío para auto-generación segura)."
                )
        # 3. Orígenes CORS: incluir el origen público configurado y los extra
        origins = list(self.BACKEND_CORS_ORIGINS)
        for candidate in [self.SERVER_PUBLIC_URL, *self.CORS_EXTRA_ORIGINS]:
            candidate = (candidate or "").strip().rstrip("/")
            if candidate and candidate not in origins:
                origins.append(candidate)
        self.BACKEND_CORS_ORIGINS = origins
        return self


settings = Settings()

