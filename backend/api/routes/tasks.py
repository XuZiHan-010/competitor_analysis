from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from api.dependencies import run_manager
from schemas.scope import TaskScopeContract
from schemas.traces import AgentTrace
from services.runs.manager import RunRecord

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class RunRequest(BaseModel):
    scope_contract: TaskScopeContract
    force_feedback_demo: bool = False


@router.post("/{task_id}/run", response_model=RunRecord)
async def run_task(
    task_id: UUID, request: RunRequest, background_tasks: BackgroundTasks
) -> RunRecord:
    if request.scope_contract.id != task_id:
        raise HTTPException(status_code=400, detail="task_id does not match scope_contract.id")
    record = await run_manager.start_run(
        request.scope_contract,
        force_feedback_demo=request.force_feedback_demo,
    )
    state = run_manager.build_initial_state(
        record,
        request.scope_contract,
        force_feedback_demo=request.force_feedback_demo,
    )
    # DAG runs in the background; client subscribes to SSE for progress.
    background_tasks.add_task(run_manager.execute_run, record.id, state)
    return record


@router.get("/{run_id}/timeline", response_model=list[AgentTrace])
async def get_timeline(run_id: UUID) -> list[AgentTrace]:
    run = await run_manager.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return await run_manager.get_timeline(run_id)
