from typing import Literal

from schemas.survey import SurveyEvidence
from services.survey.redaction import redact_sensitive_text


def parse_uploaded_survey(
    *,
    content: str,
    kind: Literal["questionnaire_result", "interview_record"],
) -> list[SurveyEvidence]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines and content.strip():
        lines = [content.strip()]
    return [
        SurveyEvidence(
            source_type="user_uploaded_primary",
            content=redact_sensitive_text(line),
            redacted=True,
        )
        for line in lines
    ]
