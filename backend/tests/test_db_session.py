import pytest

from db.session import database_url_for_async


def test_database_url_for_async_converts_postgres_urls() -> None:
    assert (
        database_url_for_async("postgresql://user:pass@example.com/db")
        == "postgresql+psycopg://user:pass@example.com/db"
    )
    assert (
        database_url_for_async("postgres://user:pass@example.com/db")
        == "postgresql+psycopg://user:pass@example.com/db"
    )


def test_database_url_for_async_rejects_missing_leading_p() -> None:
    with pytest.raises(ValueError, match="postgresql:// or postgres://"):
        database_url_for_async("ostgresql://user:pass@example.com/db")
