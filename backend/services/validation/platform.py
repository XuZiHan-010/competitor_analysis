from collections.abc import Awaitable
from typing import Any, cast

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from db.session import database_url_for_async
from settings import get_settings


class DbReadiness(BaseModel):
    configured: bool
    connected: bool = False
    vector_extension: bool = False
    embedding_columns: dict[str, bool] = Field(default_factory=dict)
    embedding_counts: dict[str, int] = Field(default_factory=dict)
    alembic_revision: str | None = None
    error: str | None = None


class RedisReadiness(BaseModel):
    configured: bool
    connected: bool = False
    error: str | None = None


class PlatformReadiness(BaseModel):
    passed: bool
    mode: str
    db: DbReadiness
    redis: RedisReadiness
    required_env_present: dict[str, bool]


async def check_platform_readiness() -> PlatformReadiness:
    settings = get_settings()
    db = await _check_db(settings.database_url)
    redis = await _check_redis(settings.redis_dsn)
    required_env_present = {
        "DATABASE_URL": bool(settings.database_url),
        "REDIS_URL": bool(settings.redis_url),
        "JWT_SECRET": bool(settings.jwt_secret),
        "OPENAI_API_KEY": bool(settings.openai_api_key),
        "GEMINI_API_KEY": bool(settings.gemini_api_key),
        "DEEPSEEK_API_KEY": bool(settings.deepseek_api_key),
        "TAVILY_API_KEY": bool(settings.tavily_api_key),
        "SERPAPI_API_KEY": bool(settings.serpapi_api_key),
    }
    return PlatformReadiness(
        passed=(
            db.configured
            and db.connected
            and db.vector_extension
            and all(db.embedding_columns.values())
            and redis.configured
            and redis.connected
        ),
        mode="mock" if settings.mock_llm else "real",
        db=db,
        redis=redis,
        required_env_present=required_env_present,
    )


async def _check_db(database_url: str | None) -> DbReadiness:
    if not database_url:
        return DbReadiness(configured=False)
    engine = create_async_engine(database_url_for_async(database_url), pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            vector_extension = bool(
                (
                    await conn.execute(
                        text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                    )
                ).scalar_one()
            )
            embedding_columns = {
                "reports.embedding": await _column_exists(conn, "reports", "embedding"),
                "report_claims.embedding": await _column_exists(
                    conn, "report_claims", "embedding"
                ),
                "source_citations.embedding": await _column_exists(
                    conn, "source_citations", "embedding"
                ),
            }
            embedding_counts = {
                "reports": await _embedding_count(conn, "reports"),
                "report_claims": await _embedding_count(conn, "report_claims"),
                "source_citations": await _embedding_count(conn, "source_citations"),
            }
            alembic_revision = await _alembic_revision(conn)
            return DbReadiness(
                configured=True,
                connected=True,
                vector_extension=vector_extension,
                embedding_columns=embedding_columns,
                embedding_counts=embedding_counts,
                alembic_revision=alembic_revision,
            )
    except Exception as exc:
        return DbReadiness(configured=True, error=f"{exc.__class__.__name__}: {exc}")
    finally:
        await engine.dispose()


async def _check_redis(redis_url: str | None) -> RedisReadiness:
    if not redis_url:
        return RedisReadiness(configured=False)
    try:
        from redis.asyncio import Redis

        redis: Redis = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        try:
            connected = bool(await cast(Awaitable[bool], redis.ping()))
        finally:
            await redis.aclose()
        return RedisReadiness(configured=True, connected=connected)
    except Exception as exc:
        return RedisReadiness(configured=True, error=f"{exc.__class__.__name__}: {exc}")


async def _column_exists(conn: Any, table_name: str, column_name: str) -> bool:
    result = await conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                  AND column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return bool(result.scalar_one())


async def _embedding_count(conn: Any, table_name: str) -> int:
    try:
        result = await conn.execute(
            text(f"SELECT COUNT(*) FROM {table_name} WHERE embedding IS NOT NULL")
        )
        return int(result.scalar_one())
    except Exception:
        return 0


async def _alembic_revision(conn: Any) -> str | None:
    try:
        result = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        value = result.scalar_one_or_none()
    except Exception:
        return None
    return str(value) if value is not None else None
