from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from schemas.survey import SurveyUploadResponse
from services.survey import parse_uploaded_survey

router = APIRouter(prefix="/api/tasks", tags=["survey"])


class SurveyUploadRequest(BaseModel):
    kind: Literal["questionnaire_result", "interview_record"]
    content: str


@router.post("/{task_id}/survey/upload", response_model=SurveyUploadResponse)
async def upload_survey(task_id: UUID, request: SurveyUploadRequest) -> SurveyUploadResponse:
    evidence = parse_uploaded_survey(content=request.content, kind=request.kind)
    return SurveyUploadResponse(
        task_id=task_id,
        kind=request.kind,
        parsed_evidence_count=len(evidence),
        evidence=evidence,
    )
