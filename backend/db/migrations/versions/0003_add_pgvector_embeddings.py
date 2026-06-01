"""Add pgvector embedding columns for semantic report search.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-30
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE source_citations ADD COLUMN IF NOT EXISTS embedding vector(1536)")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS embedding vector(1536)")
    op.execute("ALTER TABLE report_claims ADD COLUMN IF NOT EXISTS embedding vector(1536)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_reports_embedding "
        "ON reports USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_claims_embedding "
        "ON report_claims USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_source_citations_embedding "
        "ON source_citations USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_source_citations_embedding")
    op.execute("DROP INDEX IF EXISTS idx_report_claims_embedding")
    op.execute("DROP INDEX IF EXISTS idx_reports_embedding")
    op.execute("ALTER TABLE report_claims DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE source_citations DROP COLUMN IF EXISTS embedding")
