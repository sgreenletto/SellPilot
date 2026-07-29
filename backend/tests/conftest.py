import re
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sellpilot.core.config import Settings, get_settings
from sellpilot.core.security import hash_password
from sellpilot.db.base import Base
from sellpilot.db.models.user import User
from sellpilot.db.session import get_db_session
from sellpilot.main import create_app
from tests.postgres import ensure_test_database_url, reset_test_schema

TEST_PASSWORD = "CorrectHorseBattery1!"
TEST_JWT_SECRET = "test-only-jwt-secret-with-at-least-32-characters"


@pytest.fixture
def tmp_path(request) -> AsyncIterator[Path]:
    root = Path(__file__).parent / ".tmp"
    root.mkdir(mode=0o777, exist_ok=True)
    test_name = re.sub(r"[^a-zA-Z0-9_-]", "_", request.node.name)[:60]
    path = root / f"{test_name}-{uuid4().hex}"
    path.mkdir(mode=0o777)
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session")
def postgres_test_database_url() -> str:
    database_url = ensure_test_database_url()
    reset_test_schema(database_url)
    return database_url


@pytest.fixture
def test_settings(postgres_test_database_url: str) -> Settings:
    return Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=postgres_test_database_url,
        JWT_SECRET_KEY=TEST_JWT_SECRET,
        PLATFORM_ADAPTER="mock",
    )


@pytest_asyncio.fixture
async def session_factory(
    test_settings: Settings,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(test_settings.database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


@pytest_asyncio.fixture
async def admin_user(
    session_factory: async_sessionmaker[AsyncSession],
) -> User:
    async with session_factory() as database_session:
        user = User(
            username="admin",
            password_hash=hash_password(TEST_PASSWORD),
            role="ADMIN",
            is_active=True,
        )
        database_session.add(user)
        await database_session.commit()
        await database_session.refresh(user)
        return user


@pytest_asyncio.fixture
async def client_bundle(
    test_settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[
    tuple[
        httpx.AsyncClient,
        object,
        async_sessionmaker[AsyncSession],
        Settings,
    ]
]:
    application = create_app(test_settings)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as database_session:
            try:
                yield database_session
                await database_session.commit()
            except Exception:
                await database_session.rollback()
                raise

    application.dependency_overrides[get_db_session] = override_session
    application.dependency_overrides[get_settings] = lambda: test_settings
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, application, session_factory, test_settings
