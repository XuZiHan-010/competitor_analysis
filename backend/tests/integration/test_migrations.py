from collections.abc import Iterator

import psycopg
import pytest
from alembic import command
from alembic.config import Config

pytestmark = pytest.mark.integration


@pytest.fixture
def alembic_config(migrated_database_url: str) -> Iterator[Config]:
    config = Config("alembic.ini")
    yield config


def test_empty_database_migrates_to_head_with_pgvector(
    migrated_database_url: str,
) -> None:
    with psycopg.connect(migrated_database_url) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        vector_enabled = connection.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        ).fetchone()
        embedding_columns = connection.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND column_name = 'embedding'
              AND table_name IN ('reports', 'report_claims', 'source_citations')
            """
        ).fetchone()

    assert revision == ("0003",)
    assert vector_enabled == (True,)
    assert embedding_columns == (3,)


def test_alembic_metadata_has_no_drift(alembic_config: Config) -> None:
    command.check(alembic_config)


def test_latest_migration_downgrades_and_upgrades_cleanly(
    alembic_config: Config,
    migrated_database_url: str,
) -> None:
    try:
        command.downgrade(alembic_config, "-1")
        with psycopg.connect(migrated_database_url) as connection:
            revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
            embedding_column = connection.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'reports'
                      AND column_name = 'embedding'
                )
                """
            ).fetchone()
        assert revision == ("0002",)
        assert embedding_column == (False,)
    finally:
        command.upgrade(alembic_config, "head")
