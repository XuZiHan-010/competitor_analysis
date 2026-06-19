from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

SourceType = Literal[
    "official",
    "media",
    "user_feedback",
    "tech_community",
    "commercial",
    "user_uploaded",
    "published_survey",
    "public_review",
    "app_review",
    "ai_simulated",
]

SourceCategory = Literal[
    "official",
    "media",
    "user_feedback",
    "tech_community",
    "commercial",
    "academic_sample",
    "unknown",
]


class SourceCitation(BaseModel):
    id: str
    type: SourceType
    category: SourceCategory = "unknown"
    url: HttpUrl | None = None
    title: str
    snippet: str
    raw_content: str | None = None
    provider: str = "mock"
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid: bool = True
    # Which scope dimension this source was gathered for (enables Analyst routing)
    dimension_id: str | None = None
