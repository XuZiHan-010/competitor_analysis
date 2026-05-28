"""Initial schema: PRD database tables.

Revision ID: 0001
Revises:
Create Date: 2026-05-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), unique=True, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("target_product", sa.Text()),
        sa.Column("target_brief", sa.Text(), nullable=False),
        sa.Column("competitor_names", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("dimensions", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_tasks_user_created", "tasks", ["user_id", sa.text("created_at DESC")])

    op.create_table(
        "task_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("langgraph_thread_id", sa.Text()),
        sa.Column("checkpoint_id", sa.Text()),
        sa.Column("error_summary", postgresql.JSONB()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "agent_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("task_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.Text(), nullable=False),
        sa.Column("node_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("input_payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("output_payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("tokens_in", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens_out", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "cost_usd", sa.Numeric(precision=12, scale=8), server_default="0", nullable=False
        ),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("langsmith_run_id", sa.Text()),
        sa.Column("decision_meta", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("task_run_id", "sequence_no"),
    )
    op.create_index("idx_agent_traces_run_sequence", "agent_traces", ["task_run_id", "sequence_no"])

    op.create_table(
        "source_citations",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), server_default="unknown", nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("raw_content", sa.Text()),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("valid", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("fetched_by_agent", sa.Text()),
    )

    op.create_table(
        "competitor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("competitor_name", sa.Text(), nullable=False),
        sa.Column("feature_tree", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("pricing", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("user_personas", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("swot", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("review_summary", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "cross_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("feature_matrix", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("pricing_comparison", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("positioning_map", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("differentiation_summary", sa.Text()),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("structured_content", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(8), server_default="zh", nullable=False),
        sa.Column("source_report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id")),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("qa_status", sa.Text(), server_default="issues", nullable=False),
        sa.Column("qa_issues", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("metrics", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("idx_reports_task_created", "reports", ["task_id", sa.text("created_at DESC")])

    op.create_table(
        "report_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claim_path", sa.Text(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("layer", sa.Text(), nullable=False),
        sa.Column("field_type", sa.Text(), nullable=False),
        sa.Column("source_ids", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("generating_agent", sa.Text(), nullable=False),
        sa.Column("qa_status", sa.Text(), server_default="pass", nullable=False),
        sa.Column("source_support", sa.Text(), server_default="unchecked", nullable=False),
        sa.Column("validity", sa.Text(), server_default="unknown", nullable=False),
        sa.Column("edit_status", sa.Text(), server_default="untouched", nullable=False),
        sa.Column("review_status", sa.Text(), server_default="unreviewed", nullable=False),
        sa.Column("correction_type", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("idx_report_claims_report", "report_claims", ["report_id"])

    op.create_table(
        "manual_corrections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_claims.id", ondelete="SET NULL"),
        ),
        sa.Column("field_path", sa.Text(), nullable=False),
        sa.Column("old_value", postgresql.JSONB()),
        sa.Column("new_value", postgresql.JSONB(), nullable=False),
        sa.Column("correction_type", sa.Text(), nullable=False),
        sa.Column("triggered_rerun", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "survey_uploads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("original_size", sa.Integer(), nullable=False),
        sa.Column("redacted_content", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("parsed_evidence_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("survey_uploads")
    op.drop_table("manual_corrections")
    op.drop_index("idx_report_claims_report")
    op.drop_table("report_claims")
    op.drop_index("idx_reports_task_created")
    op.drop_table("reports")
    op.drop_table("cross_analyses")
    op.drop_table("competitor_profiles")
    op.drop_table("source_citations")
    op.drop_index("idx_agent_traces_run_sequence")
    op.drop_table("agent_traces")
    op.drop_table("task_runs")
    op.drop_index("idx_tasks_user_created")
    op.drop_table("tasks")
    op.drop_table("users")
