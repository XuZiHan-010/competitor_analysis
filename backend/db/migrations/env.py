import asyncio
import selectors
import sys
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from db.models import Base
from db.session import database_url_for_async
from settings import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_RAW_VECTOR_COLUMNS = {
    ("source_citations", "embedding"),
    ("reports", "embedding"),
    ("report_claims", "embedding"),
}
_RAW_VECTOR_INDEXES = {
    "idx_source_citations_embedding",
    "idx_reports_embedding",
    "idx_report_claims_embedding",
}


def include_object(
    object_: Any,
    name: str | None,
    object_type: str,
    reflected: bool,
    compare_to: Any,
) -> bool:
    if reflected and compare_to is None and object_type == "column":
        table_name = getattr(getattr(object_, "table", None), "name", None)
        if (table_name, name) in _RAW_VECTOR_COLUMNS:
            return False
    return not (
        reflected
        and compare_to is None
        and object_type == "index"
        and name in _RAW_VECTOR_INDEXES
    )


def get_database_url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL must be set for migrations")
    return database_url_for_async(url)


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Any) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_database_url()
    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        try:
            loop.run_until_complete(run_async_migrations())
        finally:
            loop.close()
        return
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
