from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from api.auth_deps import CurrentUserDep
from api.dependencies import run_manager, stream_bridge
from schemas.events import StreamEvent

router = APIRouter(prefix="/api/tasks", tags=["stream"])


def _format_sse(event: StreamEvent) -> str:
    # Heartbeats are SSE comments (no id/event/data) so the browser never
    # stores their id as Last-Event-ID; otherwise a reconnect would resume from
    # a heartbeat id that collides with a real event's id and skip it.
    if event.event == "__heartbeat__":
        return ": heartbeat\n\n"
    return f"id: {event.id}\nevent: {event.event}\ndata: {event.model_dump_json()}\n\n"


@router.get("/{run_id}/events")
async def stream_events(
    run_id: UUID,
    current_user: CurrentUserDep,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    run = await run_manager.get_run(run_id)
    if run is None or run.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="stream not available")
    parsed_event_id = int(last_event_id) if last_event_id and last_event_id.isdigit() else None

    async def event_generator() -> AsyncIterator[str]:
        async for event in stream_bridge.subscribe(str(run_id), last_event_id=parsed_event_id):
            yield _format_sse(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        # Defeat proxy buffering on the backend→edge hop so heartbeats reach the
        # client in real time and idle HTTP/2 streams aren't reset mid-run.
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
