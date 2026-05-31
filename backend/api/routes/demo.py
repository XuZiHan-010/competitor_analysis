from uuid import UUID

from fastapi import APIRouter, HTTPException

from api.dependencies import run_manager
from schemas.demo import DemoReplayBundle, DemoReplaySnapshotResponse
from services.demo_replay import (
    DemoReplayUnavailableError,
    build_demo_replay_snapshot,
    load_demo_replay_bundle,
)

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/replay", response_model=DemoReplayBundle)
async def get_demo_replay() -> DemoReplayBundle:
    try:
        return load_demo_replay_bundle()
    except DemoReplayUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/replay/snapshot", response_model=DemoReplaySnapshotResponse)
async def snapshot_demo_replay(
    task_id: UUID,
    run_id: UUID,
    write_to_fixture: bool = False,
) -> DemoReplaySnapshotResponse:
    try:
        return await build_demo_replay_snapshot(
            run_manager,
            task_id=task_id,
            run_id=run_id,
            write_to_fixture=write_to_fixture,
        )
    except DemoReplayUnavailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
