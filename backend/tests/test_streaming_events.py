from uuid import uuid4

import pytest

from api.routes.stream import _format_sse
from schemas.events import StreamEvent
from schemas.traces import AgentTrace
from services.runs.manager import RunTraceContext
from services.storage import InMemoryStore
from services.streaming.bridge import InMemoryStreamBridge


def _trace(status: str) -> AgentTrace:
    run_id = uuid4()
    return AgentTrace(
        task_run_id=run_id,
        sequence_no=1,
        agent_name="CollectorAgent",
        node_name="run_collector",
        status=status,
        prompt="Collect public sources.",
        input_payload={},
        output_payload={"output_summary": "collected sources"},
    )


@pytest.mark.asyncio
async def test_trace_context_publishes_node_events() -> None:
    run_id = uuid4()
    bridge = InMemoryStreamBridge()
    context = RunTraceContext(run_id=run_id, store=InMemoryStore(), bridge=bridge)

    await context.publish_trace(_trace("succeeded"))
    await context.publish_trace(_trace("failed"))
    await context.publish_trace(_trace("retried"))

    stream = bridge.subscribe(str(run_id))
    try:
        succeeded = await anext(stream)
        failed = await anext(stream)
        retried = await anext(stream)
    finally:
        await stream.aclose()

    assert succeeded.event == "node.succeeded"
    assert failed.event == "node.failed"
    assert retried.event == "node.succeeded"


def test_heartbeat_renders_as_comment_without_id() -> None:
    # Heartbeats must be SSE comments so the browser never stores their id as
    # Last-Event-ID — otherwise a reconnect resumes from the wrong point and
    # skips a real event whose id collided with the heartbeat's.
    heartbeat = StreamEvent(id=0, run_id="run-1", event="__heartbeat__")
    rendered = _format_sse(heartbeat)

    assert "id:" not in rendered
    assert "event:" not in rendered
    assert rendered.endswith("\n\n")


def test_named_event_still_carries_id() -> None:
    event = StreamEvent(id=7, run_id="run-1", event="node.succeeded", data={"k": "v"})
    rendered = _format_sse(event)

    assert "id: 7\n" in rendered
    assert "event: node.succeeded\n" in rendered
