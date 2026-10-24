import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from app.core.config import settings
from app.core.database import engine, Base, async_session_maker
from app.domains.auth.models import RegistrationToken

# Import all domain models so SQLAlchemy Base registers their table definitions
import app.domains.admin.models
import app.domains.auth.models
import app.domains.households.models
import app.domains.integrations.models
import app.domains.catalog.models
import app.domains.receipts.models
import app.domains.shopping.models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure all database tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Bootstrap initial registration token & superadmin if needed
    async with async_session_maker() as session:
        has_tokens = (await session.execute(select(RegistrationToken))).scalars().first()
        if not has_tokens:
            bootstrap_token = RegistrationToken(
                id=uuid.uuid4(),
                token="SUPERDATO-INIT-2026",
                note="Token inicial de bienvenida para el primer administrador",
                max_uses=1,
                times_used=0,
                is_active=True,
            )
            session.add(bootstrap_token)
            await session.commit()
        else:
            # Enforce single-use constraint on initial bootstrap token if it was previously initialized with 50 uses
            init_token = (
                await session.execute(
                    select(RegistrationToken).where(RegistrationToken.token == "SUPERDATO-INIT-2026")
                )
            ).scalar_one_or_none()
            if init_token and init_token.max_uses > 1:
                init_token.max_uses = 1
                if init_token.times_used >= 1:
                    init_token.is_active = False
                await session.commit()

        # Ensure superadmin user exists and is up-to-date with compose configuration
        from app.domains.auth.models import User
        from app.domains.households.models import Household, HouseholdMembership
        from app.core.security import hash_password

        existing_user = (await session.execute(select(User).where(User.email == settings.SUPERADMIN_EMAIL.lower().strip()))).scalar_one_or_none()
        if existing_user:
            existing_user.is_superuser = True
            existing_user.hashed_password = hash_password(settings.SUPERADMIN_PASSWORD)
            await session.commit()
        else:
            new_admin = User(
                id=uuid.uuid4(),
                email=settings.SUPERADMIN_EMAIL.lower().strip(),
                hashed_password=hash_password(settings.SUPERADMIN_PASSWORD),
                full_name="Superadministrador",
                is_active=True,
                is_verified=True,
                is_superuser=True,
            )
            session.add(new_admin)
            await session.flush()

            hh = Household(
                id=uuid.uuid4(),
                name=f"Hogar de {new_admin.full_name}",
                currency="EUR",
                created_by_user_id=new_admin.id,
            )
            session.add(hh)
            await session.flush()

            membership = HouseholdMembership(
                id=uuid.uuid4(),
                household_id=hh.id,
                user_id=new_admin.id,
                role="OWNER",
            )
            session.add(membership)
            await session.commit()

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
