from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.auth_deps import CurrentUserDep
from api.dependencies import run_manager
from schemas.survey import SurveyUploadResponse
from services.survey import parse_uploaded_survey

router = APIRouter(prefix="/api/tasks", tags=["survey"])


class SurveyUploadRequest(BaseModel):
    kind: Literal["questionnaire_result", "interview_record"]
    content: str


@router.post("/{task_id}/survey/upload", response_model=SurveyUploadResponse)
async def upload_survey(
    task_id: UUID,
    request: SurveyUploadRequest,
    current_user: CurrentUserDep,
) -> SurveyUploadResponse:
    owner = await run_manager.get_task_owner(task_id)
    if owner is not None and owner != current_user.user_id:
        raise HTTPException(status_code=404, detail="task not found")
    evidence = parse_uploaded_survey(content=request.content, kind=request.kind)
    run_manager.add_survey_upload(task_id, evidence)
    return SurveyUploadResponse(
        task_id=task_id,
        kind=request.kind,
        parsed_evidence_count=len(evidence),
        evidence=evidence,
    )
