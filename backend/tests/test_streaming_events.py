from typing import Any, cast
from uuid import uuid4

import pytest

from api.routes.stream import _format_sse
from schemas.events import StreamEvent
from schemas.traces import AgentTrace
from services.runs.manager import RunTraceContext
from services.storage import InMemoryStore
from services.streaming.bridge import InMemoryStreamBridge, RedisStreamBridge


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


@pytest.mark.asyncio
async def test_in_memory_cleanup_removes_replay_events() -> None:
    run_id = "run-cleanup"
    bridge = InMemoryStreamBridge()

    await bridge.publish(run_id, "node.started", {"step": 1})
    await bridge.publish(run_id, "node.succeeded", {"step": 2})
    await bridge.cleanup(run_id)
    await bridge.publish(run_id, "run.succeeded", {"step": 3})

    stream = bridge.subscribe(run_id)
    try:
        event = await anext(stream)
    finally:
        await stream.aclose()

    assert event.id == 1
    assert event.event == "run.succeeded"
    assert event.data == {"step": 3}


class _FakeRedis:
    def __init__(self) -> None:
        self.xadd_calls: list[dict[str, Any]] = []
        self.expire_calls: list[tuple[str, int]] = []
        self.delete_calls: list[tuple[str, str]] = []

    async def incr(self, key: str) -> int:
        assert key == "task-run:redis-run:events:sequence"
        return 1

    async def xadd(self, stream_key: str, fields: dict[str, str], **kwargs: Any) -> None:
        self.xadd_calls.append({"stream_key": stream_key, "fields": fields, **kwargs})

    async def expire(self, key: str, ttl_seconds: int) -> None:
        self.expire_calls.append((key, ttl_seconds))

    async def delete(self, stream_key: str, sequence_key: str) -> None:
        self.delete_calls.append((stream_key, sequence_key))


@pytest.mark.asyncio
async def test_redis_publish_bounds_stream_and_cleanup_deletes_keys() -> None:
    fake_redis = _FakeRedis()
    bridge = RedisStreamBridge.__new__(RedisStreamBridge)
    bridge_private = cast(Any, bridge)
    bridge_private._redis = fake_redis
    bridge_private._maxlen = 3
    bridge_private._ttl_seconds = 60

    event = await bridge.publish("redis-run", "node.succeeded", {"ok": True})
    await bridge.cleanup("redis-run")

    assert event.id == 1
    assert fake_redis.xadd_calls == [
        {
            "stream_key": "task-run:redis-run:events",
            "fields": {
                "event_id": "1",
                "event": "node.succeeded",
                "data": '{"ok": true}',
                "created_at": event.created_at.isoformat(),
            },
            "id": "1-0",
            "maxlen": 3,
            "approximate": True,
        }
    ]
    assert fake_redis.expire_calls == [
        ("task-run:redis-run:events", 60),
        ("task-run:redis-run:events:sequence", 60),
    ]
    assert fake_redis.delete_calls == [
        ("task-run:redis-run:events", "task-run:redis-run:events:sequence")
    ]
