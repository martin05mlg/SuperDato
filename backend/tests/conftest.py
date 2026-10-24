import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    future=True,
)

test_async_session = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def init_test_db():
    from app.core.ratelimit import reset_rate_limits
    reset_rate_limits()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Auto-seed test registration token
    import uuid
    from app.domains.auth.models import RegistrationToken
    async with test_async_session() as session:
        token = RegistrationToken(
            id=uuid.uuid4(),
            token="TEST-TOKEN-1234",
            note="Test registration token",
            max_uses=1000,
            times_used=0,
            is_active=True,
        )
        session.add(token)
        await session.commit()

    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    async with test_async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncClient:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession):
    import uuid
    from app.domains.auth.models import User
    from app.domains.households.models import Household, HouseholdMembership

    user = User(
        id=uuid.uuid4(),
        email="test_admin@superdato.es",
        hashed_password="mock_password",
        full_name="Usuario Admin Test",
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()

    household = Household(
        id=uuid.uuid4(),
        name="Casa Principal Test",
        currency="EUR",
        created_by_user_id=user.id,
    )
    db_session.add(household)
    await db_session.flush()

    membership = HouseholdMembership(
        id=uuid.uuid4(),
        household_id=household.id,
        user_id=user.id,
        role="OWNER",
    )
    db_session.add(membership)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def auth_client(client: AsyncClient, test_user) -> AsyncClient:
    from app.core.security import create_access_token
    token = create_access_token(subject=str(test_user.id))
    client.headers["Authorization"] = f"Bearer {token}"
    return client


