import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from db.session import database_url_for_async
from settings import get_settings


def _safe_test_database_url() -> str:
    value = os.getenv("TEST_DATABASE_URL", "").strip()
    if not value:
        pytest.skip("TEST_DATABASE_URL is required for database integration tests")
    parsed = make_url(value)
    host = (parsed.host or "").lower()
    database = (parsed.database or "").lower()
    local_hosts = {"127.0.0.1", "localhost", "postgres", "pgvector"}
    if host not in local_hosts and "test" not in database:
        pytest.fail("TEST_DATABASE_URL must target localhost or a database named as a test DB")
    production_url = os.getenv("DATABASE_URL", "").strip()
    if production_url and production_url == value:
        pytest.fail("TEST_DATABASE_URL must not equal DATABASE_URL")
    return value


def _safe_test_redis_url() -> str:
    value = os.getenv("TEST_REDIS_URL", "").strip()
    if not value:
        pytest.skip("TEST_REDIS_URL is required for Redis integration tests")
    parsed = make_url(value)
    if (parsed.host or "").lower() not in {"127.0.0.1", "localhost", "redis"}:
        pytest.fail("TEST_REDIS_URL must target a local or CI Redis service")
    production_url = os.getenv("REDIS_URL", "").strip()
    if production_url and production_url == value:
        pytest.fail("TEST_REDIS_URL must not equal REDIS_URL")
    return value


@pytest.fixture(scope="session")
def migrated_database_url() -> Iterator[str]:
    value = _safe_test_database_url()
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = value
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    try:
        yield value
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_engine(migrated_database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(database_url_for_async(migrated_database_url), pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_sessionmaker(
    db_engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield factory
        finally:
            if transaction.is_active:
                await transaction.rollback()


@pytest.fixture(scope="session")
def test_redis_url() -> str:
    return _safe_test_redis_url()
