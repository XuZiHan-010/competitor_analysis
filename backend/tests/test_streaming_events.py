from collections.abc import Callable
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.dependencies import run_manager, stream_bridge
from api.routes.stream import _format_sse
from schemas.events import StreamEvent
from schemas.traces import AgentTrace
from services.agents.decorators import traced_node
from services.auth import user_id_for_email
from services.runs.manager import RunRecord, RunTraceContext
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


@traced_node(
    agent_name="TestAgent",
    node_name="run_test_node",
    prompt="Run a test node.",
)
async def _successful_node(*, trace_context: RunTraceContext) -> str:
    return "ok"


@traced_node(
    agent_name="TestAgent",
    node_name="run_test_node",
    prompt="Run a test node.",
)
async def _failing_node(*, trace_context: RunTraceContext) -> None:
    raise RuntimeError("node failed")


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


@pytest.mark.asyncio
async def test_traced_node_publishes_started_before_succeeded_without_extra_trace() -> None:
    run_id = uuid4()
    store = InMemoryStore()
    bridge = InMemoryStreamBridge()
    context = RunTraceContext(run_id=run_id, store=store, bridge=bridge)

    assert await _successful_node(trace_context=context) == "ok"

    stream = bridge.subscribe(str(run_id))
    try:
        events = [await anext(stream), await anext(stream)]
    finally:
        await stream.aclose()

    assert [event.event for event in events] == ["node.started", "node.succeeded"]
    assert events[0].data == {
        "agent_name": "TestAgent",
        "node_name": "run_test_node",
    }
    assert len(store.traces_by_run[run_id]) == 1
    assert store.traces_by_run[run_id][0].sequence_no == 1


@pytest.mark.asyncio
async def test_traced_node_publishes_started_before_failed_without_extra_trace() -> None:
    run_id = uuid4()
    store = InMemoryStore()
    bridge = InMemoryStreamBridge()
    context = RunTraceContext(run_id=run_id, store=store, bridge=bridge)

    with pytest.raises(RuntimeError, match="node failed"):
        await _failing_node(trace_context=context)

    stream = bridge.subscribe(str(run_id))
    try:
        events = [await anext(stream), await anext(stream)]
    finally:
        await stream.aclose()

    assert [event.event for event in events] == ["node.started", "node.failed"]
    assert len(store.traces_by_run[run_id]) == 1
    assert store.traces_by_run[run_id][0].sequence_no == 1


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


@pytest.mark.asyncio
async def test_in_memory_reconnect_resumes_without_duplicates_or_gaps() -> None:
    run_id = "run-reconnect"
    bridge = InMemoryStreamBridge()
    for step in range(1, 4):
        await bridge.publish(run_id, "node.succeeded", {"step": step})

    stream = bridge.subscribe(run_id, last_event_id=1)
    try:
        resumed = [await anext(stream), await anext(stream)]
    finally:
        await stream.aclose()

    assert [event.id for event in resumed] == [2, 3]
    assert [event.data["step"] for event in resumed] == [2, 3]


def test_invalid_last_event_id_safely_starts_from_available_events(
    auth_client_factory: Callable[[str], TestClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = "stream-owner@example.com"
    client = auth_client_factory(email)
    run = RunRecord(task_id=uuid4(), user_id=user_id_for_email(email))
    run_manager._runs[run.id] = run
    received: list[int | None] = []

    async def fake_subscribe(
        run_id: str,
        *,
        last_event_id: int | None = None,
    ) -> Any:
        received.append(last_event_id)
        yield StreamEvent(id=1, run_id=run_id, event="run.succeeded", data={})

    monkeypatch.setattr(stream_bridge, "subscribe", fake_subscribe)
    with client.stream(
        "GET",
        f"/api/tasks/{run.id}/events",
        headers={"Last-Event-ID": "not-a-number"},
    ) as response:
        assert response.status_code == 200
        assert any(line == "id: 1" for line in response.iter_lines())

    assert received == [None]


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
