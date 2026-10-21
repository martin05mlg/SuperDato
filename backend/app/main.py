from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import engine, Base

# Import all domain models so SQLAlchemy Base registers their table definitions
import app.domains.auth.models
import app.domains.households.models
import app.domains.integrations.models
import app.domains.catalog.models
import app.domains.receipts.models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: If using SQLite in dev or testing, auto-create tables
    if "sqlite" in settings.DATABASE_URL:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: Cleanly dispose of connection pools
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST de SuperDato para gestión, importación y analítica de tickets digitales de Mercadona.",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Domain Routers
from app.domains.auth.router import router as auth_router
from app.domains.households.router import router as households_router
from app.domains.receipts.router import router as receipts_router
from app.domains.catalog.router import router as catalog_router
from app.domains.analytics.router import router as analytics_router
from app.domains.integrations.router import router as integrations_router

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(households_router, prefix=settings.API_V1_PREFIX)
app.include_router(receipts_router, prefix=settings.API_V1_PREFIX)
app.include_router(catalog_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(integrations_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint providing basic API info and interactive documentation link."""
    return {
        "message": f"Bienvenido a {settings.APP_NAME} API",
        "docs": f"{settings.API_V1_PREFIX}/docs",
        "version": settings.APP_VERSION,
    }


@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify API availability and version."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
