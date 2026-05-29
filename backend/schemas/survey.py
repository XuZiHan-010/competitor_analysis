from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

SurveySourceType = Literal[
    "user_uploaded_primary",
    "published_survey",
    "public_review",
    "ai_simulated",
]


class SurveyQuestion(BaseModel):
    id: str = Field(default_factory=lambda: f"sq_{uuid4().hex[:8]}")
    text: str
    type: Literal["open", "multiple_choice", "scale"]
    options: list[str] | None = None
    intent: str


class Questionnaire(BaseModel):
    id: str = Field(default_factory=lambda: f"qn_{uuid4().hex[:8]}")
    competitor: str
    dimension_intent: str
    questions: list[SurveyQuestion] = Field(min_length=1, max_length=10)
    design_rationale: str


class TargetPersona(BaseModel):
    label: str
    traits: str
    est_size: Literal["majority", "significant", "niche"]
    inferred_from: list[str]


class DistributionHandle(BaseModel):
    id: str = Field(default_factory=lambda: f"dist_{uuid4().hex[:8]}")
    distributor_impl: str
    questionnaire_id: str
    target_personas: list[TargetPersona]
    sample_size: int
    status: Literal["dispatched", "collecting", "completed", "failed"]
    dispatched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SurveyResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"sr_{uuid4().hex[:8]}")
    distribution_id: str
    persona: TargetPersona
    answers: dict[str, str]
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SurveyEvidence(BaseModel):
    id: str = Field(default_factory=lambda: f"se_{uuid4().hex[:8]}")
    question_id: str
    source_type: SurveySourceType
    source_id: str
    raw_quote: str
    persona_inferred: str | None = None


class SurveyInsight(BaseModel):
    question_id: str
    point: str
    frequency: int
    representative_quotes: list[str]
    evidence_ids: list[str]
    confidence: Literal["high", "medium", "low"]


class SurveyResult(BaseModel):
    competitor: str
    dimension_intent: str
    questionnaire: Questionnaire
    target_personas: list[TargetPersona]
    distribution: DistributionHandle
    responses: list[SurveyResponse]
    evidence: list[SurveyEvidence]
    insights: list[SurveyInsight]
    coverage_note: str
    source_breakdown: dict[str, int]


class SurveyUploadResponse(BaseModel):
    task_id: UUID
    kind: Literal["questionnaire_result", "interview_record"]
    parsed_evidence_count: int
    evidence: list[SurveyEvidence]
