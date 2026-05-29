from typing import Literal

from schemas.survey import SurveyEvidence
from services.survey.redaction import redact_sensitive_text


def parse_uploaded_survey(
    *,
    content: str,
    kind: Literal["questionnaire_result", "interview_record"],
) -> list[SurveyEvidence]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    return [
        SurveyEvidence(
            question_id=f"upload_{index}",
            source_type="user_uploaded_primary",
            source_id=f"user_uploaded:{kind}:{index}",
            raw_quote=redact_sensitive_text(line),
            persona_inferred=None,
        )
        for index, line in enumerate(lines, start=1)
    ]
