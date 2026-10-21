from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import engine, Base


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
from app.domains.analytics.router import router as analytics_router

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(households_router, prefix=settings.API_V1_PREFIX)
app.include_router(receipts_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify API availability and version."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Root route
@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API. Visit {settings.API_V1_PREFIX}/docs for OpenAPI interactive documentation."
    }

