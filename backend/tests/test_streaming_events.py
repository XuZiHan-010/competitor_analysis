from uuid import uuid4

import pytest

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
