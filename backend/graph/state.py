from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.report import Report
from schemas.scope import TaskScopeContract
from schemas.source import SourceCitation
from schemas.survey import SurveyEvidence, SurveyResult


class RawCollectionResult(BaseModel):
    competitor_name: str
    sources: list[SourceCitation]
    completeness_score: float = 0.0
    skipped_urls: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ExtensionFinding(BaseModel):
    dimension_id: str
    competitor_name: str
    summary: str
    bullets: list[str] = Field(default_factory=list)
    table_data: list[dict[str, Any]] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class StructuredCompetitorProfile(BaseModel):
    competitor_name: str
    feature_tree: dict[str, Any]
    pricing: dict[str, Any]
    user_personas: list[dict[str, Any]]
    swot: dict[str, Any]
    source_ids: list[str]


class CrossCompetitorAnalysis(BaseModel):
    feature_matrix: dict[str, Any] = Field(default_factory=dict)
    pricing_comparison: dict[str, Any] = Field(default_factory=dict)
    positioning_map: dict[str, Any] = Field(default_factory=dict)
    differentiation_summary: str = ""


class QAIssue(BaseModel):
    severity: str
    target_agent: str
    target_competitor: str | None = None
    failed_field: str
    message: str
    retryable: bool = True


class QAResult(BaseModel):
    passed: bool
    issues: list[QAIssue] = Field(default_factory=list)


class WorkflowState(BaseModel):
    task_id: UUID
    run_id: UUID
    scope_contract: TaskScopeContract
    # PRD §六: keyed by competitor_name for O(1) lookup and unambiguous routing
    raw_collections: dict[str, RawCollectionResult] = Field(default_factory=dict)
    structured_profiles: dict[str, StructuredCompetitorProfile] = Field(default_factory=dict)
    extension_findings: list[ExtensionFinding] = Field(default_factory=list)
    survey_results: dict[str, SurveyResult] = Field(default_factory=dict)
    uploaded_survey_evidence: list[SurveyEvidence] = Field(default_factory=list)
    cross_analysis: CrossCompetitorAnalysis | None = None
    report: Report | None = None
    qa_result: QAResult | None = None
    feedback_signals: dict[str, Any] = Field(default_factory=dict)
    retry_counts: dict[str, int] = Field(default_factory=dict)
