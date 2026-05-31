from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime
from functools import wraps
from time import perf_counter
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from schemas.traces import AgentTrace
from services.llm.usage import collected_usage, reset_capture, start_capture

# PRD §五.X: input_price/output_price in USD per 1M tokens
_AGENT_PRICING: dict[str, tuple[float, float]] = {
    "CollectorAgent": (0.30, 2.50),  # Gemini 2.5 Flash
    "AnalystAgent": (0.435, 0.87),  # DeepSeek V4 Pro
    "WriterAgent": (0.435, 0.87),  # DeepSeek V4 Pro
    "QAAgent": (0.15, 0.60),  # gpt-4o-mini
    "ScopingAgent": (0.15, 0.60),  # gpt-4o-mini
}


class TraceContext(Protocol):
    run_id: Any

    def next_sequence(self) -> int: ...

    def record_trace(self, trace: AgentTrace) -> None: ...

    async def publish_trace(self, trace: AgentTrace) -> None: ...


T = TypeVar("T")


def _to_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return {"value": repr(value)}


def _estimate_tokens(payload: dict[str, Any]) -> int:
    return max(len(str(payload)) // 4, 1)


def _calc_cost_usd(agent_name: str, tokens_in: int, tokens_out: int) -> float:
    in_price, out_price = _AGENT_PRICING.get(agent_name, (0.15, 0.60))
    return round((tokens_in * in_price + tokens_out * out_price) / 1_000_000, 8)


def traced_node(
    agent_name: str,
    node_name: str,
    prompt: str,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            context = kwargs.get("trace_context")
            started = datetime.now(UTC)
            start = perf_counter()
            input_payload = {"args": [_to_payload(arg) for arg in args[1:]]}
            usage_token = start_capture()
            try:
                result = await func(*args, **kwargs)
                real_usage = collected_usage()
            except Exception as exc:
                if context is not None:
                    trace = AgentTrace(
                        task_run_id=context.run_id,
                        sequence_no=context.next_sequence(),
                        agent_name=agent_name,
                        node_name=node_name,
                        status="failed",
                        prompt=prompt,
                        input_payload=input_payload,
                        output_payload={"error": exc.__class__.__name__},
                        latency_ms=int((perf_counter() - start) * 1000),
                        decision_meta={"failure_reason": str(exc)},
                        started_at=started,
                        completed_at=datetime.now(UTC),
                    )
                    context.record_trace(trace)
                    await _publish_trace(context, trace)
                raise
            finally:
                reset_capture(usage_token)
            if context is not None:
                output_payload = _to_payload(result)
                if real_usage is not None:
                    tokens_in, tokens_out = real_usage
                else:
                    tokens_in = _estimate_tokens(input_payload)
                    tokens_out = _estimate_tokens(output_payload)
                trace = AgentTrace(
                    task_run_id=context.run_id,
                    sequence_no=context.next_sequence(),
                    agent_name=agent_name,
                    node_name=node_name,
                    status="succeeded",
                    prompt=prompt,
                    input_payload=input_payload,
                    output_payload=output_payload,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=_calc_cost_usd(agent_name, tokens_in, tokens_out),
                    latency_ms=int((perf_counter() - start) * 1000),
                    started_at=started,
                    completed_at=datetime.now(UTC),
                )
                context.record_trace(trace)
                await _publish_trace(context, trace)
            return result

        return wrapper

    return decorator


async def _publish_trace(context: TraceContext, trace: AgentTrace) -> None:
    with suppress(Exception):
        await context.publish_trace(trace)
