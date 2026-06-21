import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, Protocol

from schemas.events import StreamEvent


class StreamBridge(Protocol):
    async def publish(self, run_id: str, event: str, data: dict) -> StreamEvent: ...

    def subscribe(
        self,
        run_id: str,
        *,
        last_event_id: int | None = None,
    ) -> AsyncIterator[StreamEvent]: ...

    async def cleanup(self, run_id: str) -> None: ...


class InMemoryStreamBridge:
    def __init__(self) -> None:
        self._events: dict[str, list[StreamEvent]] = defaultdict(list)
        self._subscribers: dict[str, list[asyncio.Queue[StreamEvent]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, run_id: str, event: str, data: dict) -> StreamEvent:
        async with self._lock:
            next_id = len(self._events[run_id]) + 1
            stream_event = StreamEvent(id=next_id, run_id=run_id, event=event, data=data)
            self._events[run_id].append(stream_event)
            subscribers = list(self._subscribers[run_id])
        for queue in subscribers:
            await queue.put(stream_event)
        return stream_event

    async def cleanup(self, run_id: str) -> None:
        async with self._lock:
            self._events.pop(run_id, None)
            self._subscribers.pop(run_id, None)

    async def subscribe(
        self,
        run_id: str,
        *,
        last_event_id: int | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        async with self._lock:
            replay = [
                event
                for event in self._events[run_id]
                if last_event_id is None or event.id > last_event_id
            ]
            self._subscribers[run_id].append(queue)
        try:
            for event in replay:
                yield event
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    # id is unused: heartbeats render as SSE comments (see
                    # api.routes.stream._format_sse), so they never advance the
                    # client's Last-Event-ID.
                    yield StreamEvent(id=0, run_id=run_id, event="__heartbeat__")
                    continue
                yield event
        finally:
            async with self._lock:
                self._subscribers[run_id].remove(queue)


class RedisStreamBridge:
    def __init__(
        self,
        redis_url: str,
        *,
        maxlen: int = 2000,
        ttl_seconds: int = 86400,
    ) -> None:
        from redis.asyncio import Redis

        self._redis: Redis = Redis.from_url(redis_url, decode_responses=True)
        self._maxlen = maxlen
        self._ttl_seconds = ttl_seconds

    async def publish(self, run_id: str, event: str, data: dict) -> StreamEvent:
        sequence_key = self._sequence_key(run_id)
        stream_key = self._stream_key(run_id)
        event_id = int(await self._redis.incr(sequence_key))
        stream_event = StreamEvent(id=event_id, run_id=run_id, event=event, data=data)
        # maxlen+TTL keep the per-run event log bounded; without them every run's
        # stream accrues forever and eventually exhausts Redis maxmemory, which a
        # noeviction instance answers by rejecting all writes (OutOfMemoryError).
        await self._redis.xadd(
            stream_key,
            {
                "event_id": str(event_id),
                "event": event,
                "data": json.dumps(data),
                "created_at": stream_event.created_at.isoformat(),
            },
            id=f"{event_id}-0",
            maxlen=self._maxlen,
            approximate=True,
        )
        await self._redis.expire(stream_key, self._ttl_seconds)
        await self._redis.expire(sequence_key, self._ttl_seconds)
        return stream_event

    async def cleanup(self, run_id: str) -> None:
        await self._redis.delete(self._stream_key(run_id), self._sequence_key(run_id))

    async def subscribe(
        self,
        run_id: str,
        *,
        last_event_id: int | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        stream_key = self._stream_key(run_id)
        last_id = f"{last_event_id or 0}-0"
        while True:
            # redis-py types xread's result inconsistently across versions; widen
            # to Any so unpacking the (stream, [(id, fields)]) shape type-checks.
            response: Any = await self._redis.xread({stream_key: last_id}, block=15_000, count=20)
            if not response:
                # id is unused: heartbeats render as SSE comments, so they never
                # advance the client's Last-Event-ID (see _format_sse).
                yield StreamEvent(id=0, run_id=run_id, event="__heartbeat__")
                continue
            for _, messages in response:
                for redis_id, fields in messages:
                    last_id = redis_id
                    yield self._event_from_fields(run_id, fields)

    def _event_from_fields(self, run_id: str, fields: dict[str, Any]) -> StreamEvent:
        return StreamEvent(
            id=int(fields["event_id"]),
            run_id=run_id,
            event=fields["event"],
            data=json.loads(fields.get("data") or "{}"),
        )

    def _stream_key(self, run_id: str) -> str:
        return f"task-run:{run_id}:events"

    def _sequence_key(self, run_id: str) -> str:
        return f"task-run:{run_id}:events:sequence"
