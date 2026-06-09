from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from settings import get_settings


def database_url_for_async(url: str) -> str:
    value = url.strip()
    if value.startswith(("ostgresql://", "ostgresql+")):
        raise ValueError("DATABASE_URL must start with postgresql:// or postgres://")
    if value.startswith("postgresql+"):
        return value
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    raise ValueError("DATABASE_URL must start with postgresql:// or postgres://")


def create_engine() -> AsyncEngine:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required")
    return create_async_engine(database_url_for_async(settings.database_url), pool_pre_ping=True)


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def iter_session() -> AsyncIterator[AsyncSession]:
    engine = create_engine()
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as session:
        yield session
    await engine.dispose()
