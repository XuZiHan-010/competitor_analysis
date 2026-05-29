from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class CompetitorCandidate(BaseModel):
    name: str
    source: Literal["user_chip", "nl_extracted", "ai_recommended"]
    rationale: str | None = None


class ScopeDimension(BaseModel):
    id: str
    title: str
    intent: str
    layer: Literal["core", "extension"]
    order: int
    enabled: bool = True
    locked: bool = False
    # "system" for core dims, "ai_suggested"/"user_added" for extension dims
    source: Literal["system", "ai_suggested", "user_added"] = "system"
    # Points to the fixed Schema name for core dims; None for extension dims
    schema_ref: str | None = None


class SurveyQuestion(BaseModel):
    id: str
    text: str
    question_type: Literal["single_choice", "multi_choice", "scale", "free_text"]
    options: list[str] = Field(default_factory=list)


class UserResearchPlan(BaseModel):
    enabled: bool = False
    questionnaire: list[SurveyQuestion] = Field(default_factory=list)
    interview_outline: list[str] = Field(default_factory=list)
    # UI hint: whether user intends to upload real survey data
    prefer_upload: bool = False


class TaskScopeContract(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_brief: str
    intent_mode: Literal["list", "intent", "mixed"]
    # Optional: the user's own product being compared against competitors
    target_product: str | None = None
    competitors: list[CompetitorCandidate]
    clarifications: list[dict] = Field(default_factory=list)
    dimensions: list[ScopeDimension]
    user_research_plan: UserResearchPlan = Field(default_factory=UserResearchPlan)
    # Set when user clicks "Confirm → Start analysis"; object becomes read-only after
    frozen_at: datetime | None = None

    @model_validator(mode="after")
    def validate_competitors_and_dimensions(self) -> "TaskScopeContract":
        if len(self.competitors) < 3:
            raise ValueError("task scope requires at least 3 competitors")
        ai_suggested = [
            d for d in self.dimensions if d.layer == "extension" and d.source == "ai_suggested"
        ]
        if len(ai_suggested) > 4:
            raise ValueError("ScopingAgent can suggest at most 4 extension dimensions")
        return self

    def freeze(self) -> "TaskScopeContract":
        return self.model_copy(update={"frozen_at": datetime.now(UTC)})


class ScopingRequest(BaseModel):
    user_brief: str
    known_competitors: list[str] = Field(default_factory=list)
    clarifications: list[str] = Field(default_factory=list)
    previous_draft: "ScopingDraft | None" = None


class ScopingDraft(BaseModel):
    scope_contract: TaskScopeContract
    clarification_questions: list[str]
    rationale: str
