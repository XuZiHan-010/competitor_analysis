from uuid import uuid4

import pytest

from services.streaming.bridge import RedisStreamBridge

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_redis_stream_resume_and_cleanup(test_redis_url: str) -> None:
    bridge = RedisStreamBridge(test_redis_url, maxlen=10, ttl_seconds=60)
    run_id = str(uuid4())
    try:
        await bridge.publish(run_id, "node.started", {"step": 1})
        await bridge.publish(run_id, "node.succeeded", {"step": 2})
        stream = bridge.subscribe(run_id, last_event_id=1)
        try:
            resumed = await anext(stream)
        finally:
            await stream.aclose()
        assert resumed.id == 2
        assert resumed.data == {"step": 2}

        await bridge.cleanup(run_id)
        assert await bridge._redis.exists(bridge._stream_key(run_id)) == 0
        assert await bridge._redis.exists(bridge._sequence_key(run_id)) == 0
    finally:
        await bridge.cleanup(run_id)
        await bridge._redis.aclose()
