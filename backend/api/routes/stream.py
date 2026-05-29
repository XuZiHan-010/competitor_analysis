from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from api.dependencies import stream_bridge
from schemas.events import StreamEvent

router = APIRouter(prefix="/api/tasks", tags=["stream"])


def _format_sse(event: StreamEvent) -> str:
    return f"id: {event.id}\nevent: {event.event}\ndata: {event.model_dump_json()}\n\n"


@router.get("/{run_id}/events")
async def stream_events(
    run_id: UUID,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    parsed_event_id = int(last_event_id) if last_event_id and last_event_id.isdigit() else None

    async def event_generator() -> AsyncIterator[str]:
        async for event in stream_bridge.subscribe(str(run_id), last_event_id=parsed_event_id):
            yield _format_sse(event)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
