from uuid import UUID

from fastapi import APIRouter, HTTPException

from agents.scoping import ScopingAgent
from api.dependencies import run_manager
from schemas.scope import ScopingDraft, ScopingRequest

router = APIRouter(prefix="/api/tasks", tags=["scoping"])


@router.post("/scoping", response_model=ScopingDraft)
async def create_scoping_draft(request: ScopingRequest) -> ScopingDraft:
    draft = await ScopingAgent().run(request)
    run_manager.save_scoping_draft(draft)
    return draft


@router.get("/scoping/drafts/{task_id}", response_model=ScopingDraft)
async def get_scoping_draft(task_id: UUID) -> ScopingDraft:
    draft = run_manager.get_scoping_draft(task_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="scoping draft not found")
    return draft
