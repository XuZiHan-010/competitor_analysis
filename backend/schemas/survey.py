from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

SurveySourceType = Literal[
    "user_uploaded_primary",
    "published_survey",
    "public_review",
    "ai_simulated",
]


class SurveyEvidence(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source_type: SurveySourceType
    source_id: str | None = None
    content: str
    redacted: bool = True


class SurveyInsight(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    summary: str
    evidence_ids: list[str]
    source_support: Literal["supported", "weak", "unsupported"] = "supported"


class SurveyResult(BaseModel):
    competitor_name: str
    evidence: list[SurveyEvidence]
    insights: list[SurveyInsight]
    source_breakdown: dict[str, int]


class SurveyUploadResponse(BaseModel):
    task_id: UUID
    kind: Literal["questionnaire_result", "interview_record"]
    parsed_evidence_count: int
    evidence: list[SurveyEvidence]
