from uuid import UUID

from fastapi import APIRouter, HTTPException

from agents.scoping import ScopingAgent
from api.auth_deps import CurrentUserDep
from api.dependencies import run_manager
from schemas.scope import ScopingDraft, ScopingRequest

router = APIRouter(prefix="/api/tasks", tags=["scoping"])


@router.post("/scoping", response_model=ScopingDraft)
async def create_scoping_draft(
    request: ScopingRequest,
    current_user: CurrentUserDep,
) -> ScopingDraft:
    try:
        draft = await ScopingAgent().run(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    run_manager.save_scoping_draft(draft, user_id=current_user.user_id)
    return draft


@router.get("/scoping/drafts/{task_id}", response_model=ScopingDraft)
async def get_scoping_draft(
    task_id: UUID,
    current_user: CurrentUserDep,
) -> ScopingDraft:
    draft = run_manager.get_scoping_draft(task_id, user_id=current_user.user_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="scoping draft not found")
    return draft
