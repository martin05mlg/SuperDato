import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, async_session_maker

# Import all domain models so SQLAlchemy Base registers their table definitions
import app.domains.admin.models
import app.domains.auth.models
import app.domains.households.models
import app.domains.integrations.models
import app.domains.catalog.models
import app.domains.receipts.models
import app.domains.shopping.models

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: aplicar migraciones de esquema (Alembic) y garantizar el superadministrador
    if settings.AUTO_MIGRATE:
        from app.core.migrate import run_migrations

        await run_migrations()

    async with async_session_maker() as session:
        from app.core.bootstrap import ensure_superadmin, ensure_system_secrets, heal_inconsistent_receipt_line_prices

        await ensure_system_secrets(session)
        await ensure_superadmin(session)
        await heal_inconsistent_receipt_line_prices(session)

    yield
    # Shutdown: Cleanly dispose of connection pools
    await engine.dispose()


# Swagger/OpenAPI: siempre disponible en desarrollo; en producción solo con ENABLE_DOCS=true
_docs_enabled = settings.ENVIRONMENT.lower() != "production" or settings.ENABLE_DOCS

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST de SuperDato para gestión, importación y analítica de tickets digitales de Mercadona.",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if _docs_enabled else None,
    docs_url=f"{settings.API_V1_PREFIX}/docs" if _docs_enabled else None,
    redoc_url=f"{settings.API_V1_PREFIX}/redoc" if _docs_enabled else None,
    lifespan=lifespan,
)

# CORS Middleware: restrict regex to private local network IPs in non-production environments
cors_origin_regex = (
    r"^https?://(localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?$"
    if settings.ENVIRONMENT.lower() != "production"
    else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    """Cabeceras de seguridad básicas en las respuestas de la API."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Convierte errores de validación de Pydantic en mensajes de texto legibles sin estructuras anidadas."""
    errors = []
    for err in exc.errors():
        msg = err.get("msg", "Error de validación")
        msg = re.sub(r"^Value error,\s*", "", msg, flags=re.IGNORECASE)
        loc = err.get("loc", [])
        field = loc[-1] if loc else ""
        if field and field not in ("__root__", "body"):
            errors.append(f"{field}: {msg}")
        else:
            errors.append(msg)
    detail_msg = ". ".join(errors)
    logging.getLogger("superdato.validation").warning("Error 422 en %s: %s", request.url.path, detail_msg)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail_msg},
    )


# Domain Routers
from app.domains.auth.router import router as auth_router
from app.domains.households.router import router as households_router
from app.domains.receipts.router import router as receipts_router
from app.domains.catalog.router import router as catalog_router
from app.domains.analytics.router import router as analytics_router
from app.domains.integrations.router import router as integrations_router
from app.domains.admin.router import router as admin_router
from app.domains.shopping.router import router as shopping_router

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(households_router, prefix=settings.API_V1_PREFIX)
app.include_router(receipts_router, prefix=settings.API_V1_PREFIX)
app.include_router(catalog_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(integrations_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
app.include_router(shopping_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint providing basic API info."""
    payload = {
        "message": f"Bienvenido a {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
    }
    if _docs_enabled:
        payload["docs"] = f"{settings.API_V1_PREFIX}/docs"
    return payload


@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify API availability and version."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

