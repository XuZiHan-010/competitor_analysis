from fastapi import APIRouter

from agents.scoping import ScopingAgent
from schemas.scope import ScopingDraft, ScopingRequest

router = APIRouter(prefix="/api/tasks", tags=["scoping"])


@router.post("/scoping", response_model=ScopingDraft)
async def create_scoping_draft(request: ScopingRequest) -> ScopingDraft:
    return await ScopingAgent().run(request)
