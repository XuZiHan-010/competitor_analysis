from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tasks: Mapped[list["Task"]] = relationship(back_populates="user")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (Index("idx_tasks_user_created", "user_id", text("created_at DESC")),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    target_product: Mapped[str | None] = mapped_column(Text)
    target_brief: Mapped[str] = mapped_column(Text, nullable=False)
    competitor_names: Mapped[dict] = mapped_column(JSONB, server_default="[]", nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSONB, server_default="[]", nullable=False)
    status: Mapped[str] = mapped_column(Text, server_default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User | None] = relationship(back_populates="tasks")
    runs: Mapped[list["TaskRun"]] = relationship(back_populates="task")
    source_citations: Mapped[list["SourceCitation"]] = relationship(back_populates="task")
    reports: Mapped[list["Report"]] = relationship(back_populates="task")


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, server_default="pending", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    langgraph_thread_id: Mapped[str | None] = mapped_column(Text)
    checkpoint_id: Mapped[str | None] = mapped_column(Text)
    error_summary: Mapped[dict | None] = mapped_column(JSONB)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    task: Mapped[Task] = relationship(back_populates="runs")
    agent_traces: Mapped[list["AgentTrace"]] = relationship(back_populates="task_run")


class AgentTrace(Base):
    __tablename__ = "agent_traces"
    __table_args__ = (
        UniqueConstraint("task_run_id", "sequence_no"),
        Index("idx_agent_traces_run_sequence", "task_run_id", "sequence_no"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    task_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=False
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[str] = mapped_column(Text, nullable=False)
    node_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    output_payload: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    cost_usd: Mapped[float] = mapped_column(
        Numeric(precision=12, scale=8), server_default="0", nullable=False
    )
    latency_ms: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    langsmith_run_id: Mapped[str | None] = mapped_column(Text)
    decision_meta: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    task_run: Mapped[TaskRun] = relationship(back_populates="agent_traces")


class SourceCitation(Base):
    __tablename__ = "source_citations"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, server_default="unknown", nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    raw_content: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    # pgvector column is added in the raw SQL migration until SQLAlchemy vector type is wired.
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fetched_by_agent: Mapped[str | None] = mapped_column(Text)

    task: Mapped[Task] = relationship(back_populates="source_citations")


class CompetitorProfile(Base):
    __tablename__ = "competitor_profiles"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    competitor_name: Mapped[str] = mapped_column(Text, nullable=False)
    feature_tree: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    pricing: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    user_personas: Mapped[dict] = mapped_column(JSONB, server_default="[]", nullable=False)
    swot: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    review_summary: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CrossAnalysis(Base):
    __tablename__ = "cross_analyses"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    feature_matrix: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    pricing_comparison: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    positioning_map: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    differentiation_summary: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("idx_reports_task_created", "task_id", text("created_at DESC")),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    structured_content: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), server_default="zh", nullable=False)
    source_report_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("reports.id")
    )
    version: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    qa_status: Mapped[str] = mapped_column(Text, server_default="issues", nullable=False)
    qa_issues: Mapped[dict] = mapped_column(JSONB, server_default="[]", nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    # pgvector column is added in the raw SQL migration until SQLAlchemy vector type is wired.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    task: Mapped[Task] = relationship(back_populates="reports")
    claims: Mapped[list["ReportClaim"]] = relationship(back_populates="report")


class ReportClaim(Base):
    __tablename__ = "report_claims"
    __table_args__ = (Index("idx_report_claims_report", "report_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    report_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    claim_path: Mapped[str] = mapped_column(Text, nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    layer: Mapped[str] = mapped_column(Text, nullable=False)
    field_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_ids: Mapped[dict] = mapped_column(JSONB, server_default="[]", nullable=False)
    generating_agent: Mapped[str] = mapped_column(Text, nullable=False)
    qa_status: Mapped[str] = mapped_column(Text, server_default="pass", nullable=False)
    source_support: Mapped[str] = mapped_column(Text, server_default="unchecked", nullable=False)
    validity: Mapped[str] = mapped_column(Text, server_default="unknown", nullable=False)
    edit_status: Mapped[str] = mapped_column(Text, server_default="untouched", nullable=False)
    review_status: Mapped[str] = mapped_column(Text, server_default="unreviewed", nullable=False)
    correction_type: Mapped[str | None] = mapped_column(Text)
    # pgvector column is added in the raw SQL migration until SQLAlchemy vector type is wired.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    report: Mapped[Report] = relationship(back_populates="claims")


class ManualCorrection(Base):
    __tablename__ = "manual_corrections"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    report_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    claim_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("report_claims.id", ondelete="SET NULL")
    )
    field_path: Mapped[str] = mapped_column(Text, nullable=False)
    old_value: Mapped[dict | None] = mapped_column(JSONB)
    new_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    correction_type: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_rerun: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ScopingDraft(Base):
    __tablename__ = "scoping_drafts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    user_brief: Mapped[str] = mapped_column(Text, nullable=False)
    intent_mode: Mapped[str] = mapped_column(Text, nullable=False)
    scope_contract: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    clarification_questions: Mapped[dict] = mapped_column(
        JSONB, server_default="[]", nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    iteration: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SurveyUpload(Base):
    __tablename__ = "survey_uploads"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    original_size: Mapped[int] = mapped_column(Integer, nullable=False)
    redacted_content: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    parsed_evidence_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    uploaded_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
