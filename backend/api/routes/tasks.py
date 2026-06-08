from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from api.auth_deps import CurrentUserDep
from api.dependencies import run_manager
from schemas.scope import TaskScopeContract
from schemas.traces import AgentTrace
from services.runs.manager import RunRecord

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class RunRequest(BaseModel):
    scope_contract: TaskScopeContract
    force_feedback_demo: bool = False


@router.get("", response_model=list[RunRecord])
async def list_tasks(
    current_user: CurrentUserDep,
    limit: int = 50,
) -> list[RunRecord]:
    return await run_manager.list_runs(limit=limit, user_id=current_user.user_id)


@router.post("/{task_id}/run", response_model=RunRecord)
async def run_task(
    task_id: UUID,
    request: RunRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUserDep,
) -> RunRecord:
    if request.scope_contract.id != task_id:
        raise HTTPException(status_code=400, detail="task_id does not match scope_contract.id")
    try:
        record = await run_manager.start_run(
            request.scope_contract,
            user_id=current_user.user_id,
            user_email=current_user.email,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="task not found") from exc
    state = run_manager.build_initial_state(
        record,
        request.scope_contract,
        force_feedback_demo=request.force_feedback_demo,
    )
    # DAG runs in the background; client subscribes to SSE for progress.
    # execute_run registers its task handle so a delete can cancel it mid-flight.
    background_tasks.add_task(run_manager.execute_run, record.id, state)
    return record


@router.delete("/{run_id}", status_code=204)
async def delete_task(
    run_id: UUID,
    current_user: CurrentUserDep,
) -> None:
    deleted = await run_manager.delete_run(run_id, user_id=current_user.user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="run not found")


@router.get("/{run_id}", response_model=RunRecord)
async def get_run(
    run_id: UUID,
    current_user: CurrentUserDep,
) -> RunRecord:
    run = await run_manager.get_run(run_id)
    if run is None or run.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/{run_id}/timeline", response_model=list[AgentTrace])
async def get_timeline(
    run_id: UUID,
    current_user: CurrentUserDep,
) -> list[AgentTrace]:
    run = await run_manager.get_run(run_id)
    if run is None or run.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="run not found")
    return await run_manager.get_timeline(run_id)
