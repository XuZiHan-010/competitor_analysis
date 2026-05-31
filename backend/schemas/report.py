from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from schemas.source import SourceCitation

SourceSupport = Literal["supported", "weak", "unsupported", "unchecked"]
SourceValidity = Literal["valid", "invalid", "stale", "unknown"]
ReviewStatus = Literal["unreviewed", "correct", "partial", "wrong", "unverifiable"]
CorrectionType = Literal[
    "fact_fix",
    "wording_improvement",
    "additional_info",
    "remove_invalid",
    "structure_adjustment",
]


class ReportClaim(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    claim_path: str
    claim_text: str
    layer: Literal["core", "extension", "survey"]
    field_type: Literal["structured", "free_text"]
    source_ids: list[str]
    generating_agent: str
    qa_status: Literal["pass", "warning", "blocker"] = "pass"
    source_support: SourceSupport = "unchecked"
    validity: SourceValidity = "unknown"
    edit_status: Literal["untouched", "edited"] = "untouched"
    review_status: ReviewStatus = "unreviewed"
    correction_type: CorrectionType | None = None


class ReportMetrics(BaseModel):
    analysis_duration_seconds: float | None = None
    field_coverage_rate: float
    citation_coverage_rate: float
    manual_correction_rate: float
    human_verified_accuracy_rate: float | None = None
    source_support_rate: float | None = None
    source_type_coverage_rate: float | None = None
    invalid_source_rate: float | None = None
    rerun_rate: float | None = None
    correction_type_breakdown: dict[str, int] = Field(default_factory=dict)
    ai_self_assessment: dict[str, Any] = Field(default_factory=dict)


class Report(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    language: Literal["zh", "en"] = "zh"
    structured_content: dict[str, Any]
    markdown_content: str
    sources: list[SourceCitation]
    claims: list[ReportClaim]
    metrics: ReportMetrics
    qa_status: Literal["passed", "issues"] = "passed"
    qa_issues: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReportSearchResult(BaseModel):
    report_id: UUID
    task_id: UUID
    language: Literal["zh", "en"]
    title: str
    snippet: str
    claim_ids: list[UUID] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class ReportSearchResponse(BaseModel):
    query: str
    mode: Literal["in_memory_semantic_fallback", "pgvector"]
    results: list[ReportSearchResult]


class ReportSearchBackendResult(BaseModel):
    mode: Literal["in_memory_semantic_fallback", "pgvector"]
    reports: list[Report]


class FieldCorrectionRequest(BaseModel):
    claim_id: UUID
    field_path: str
    new_value: Any
    correction_type: CorrectionType
    triggered_rerun: bool = False


class ClaimReviewRequest(BaseModel):
    review_status: ReviewStatus


class LanguageRequest(BaseModel):
    language: Literal["zh", "en"]
