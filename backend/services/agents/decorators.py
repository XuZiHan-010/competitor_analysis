from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime
from functools import wraps
from time import perf_counter
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from schemas.traces import AgentTrace
from services.llm.usage import (
    collected_degradations,
    collected_langsmith_run_id,
    collected_usage,
    reset_capture,
    start_capture,
)

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


def _len_maybe(value: Any) -> int:
    return len(value) if hasattr(value, "__len__") else 0


def _summarize_collector(result: Any) -> str:
    if not isinstance(result, tuple) or not result:
        return _generic_summary(result)
    raw_collections = result[0]
    survey_results = result[1] if len(result) > 1 else {}
    if not isinstance(raw_collections, dict):
        return _generic_summary(result)
    source_count = sum(
        _len_maybe(getattr(item, "sources", [])) for item in raw_collections.values()
    )
    survey_count = _len_maybe(survey_results) if isinstance(survey_results, dict) else 0
    return f"采集 {len(raw_collections)} 个竞品 / 共 {source_count} 条来源 / 问卷 {survey_count} 份"


def _summarize_analyst(result: Any) -> str:
    if not isinstance(result, tuple) or len(result) < 3:
        return _generic_summary(result)
    profiles, findings, cross = result
    profile_count = len(profiles) if isinstance(profiles, dict) else 0
    finding_count = len(findings) if isinstance(findings, list) else 0
    return (
        f"结构化 {profile_count} 份画像 / {finding_count} 条扩展维度 / "
        f"交叉分析{'有' if cross is not None else '无'}"
    )


def _summarize_qa(result: Any) -> str:
    passed = getattr(result, "passed", None)
    issues = getattr(result, "issues", [])
    issue_count = _len_maybe(issues)
    if passed and issue_count == 0:
        return "QA 通过"
    blocker_count = sum(1 for issue in issues if getattr(issue, "severity", "") == "blocker")
    return f"QA 发现 {issue_count} 个问题（{blocker_count} 个 blocker）"


def _summarize_writer(result: Any) -> str:
    structured_content = getattr(result, "structured_content", {})
    claims = getattr(result, "claims", [])
    if not isinstance(structured_content, dict):
        return _generic_summary(result)
    section_count = sum(
        1
        for key in (
            "feature_tree",
            "pricing",
            "user_personas",
            "swot",
            "extensions",
            "cross_analysis",
            "survey",
        )
        if structured_content.get(key)
    )
    return f"生成报告 / {section_count} 节 / {len(claims)} 条结论"


def _generic_summary(value: Any) -> str:
    if isinstance(value, BaseModel):
        keys = list(value.model_fields.keys())[:5]
        return f"{value.__class__.__name__} / keys: {', '.join(keys)}"
    if isinstance(value, dict):
        keys = list(value.keys())[:5]
        return f"dict / keys: {', '.join(str(key) for key in keys)}"
    if isinstance(value, tuple):
        return f"tuple / {len(value)} 项"
    if isinstance(value, list):
        return f"list / {len(value)} 项"
    return value.__class__.__name__


_SUMMARIZERS: dict[str, Callable[[Any], str]] = {
    "CollectorAgent": _summarize_collector,
    "AnalystAgent": _summarize_analyst,
    "QAAgent": _summarize_qa,
    "WriterAgent": _summarize_writer,
}


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


def _output_summary(agent_name: str, result: Any) -> str:
    summarizer = _SUMMARIZERS.get(agent_name, _generic_summary)
    with suppress(Exception):
        summary = summarizer(result).strip()
        if summary:
            return summary
    return _generic_summary(result)


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
                # Read run id / degradations before `reset_capture` (finally) clears the capture.
                langsmith_run_id = collected_langsmith_run_id()
                degradations = collected_degradations()
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
                        langsmith_run_id=collected_langsmith_run_id(),
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
                summary = _output_summary(agent_name, result)
                if degradations:
                    summary = f"⚠️ LLM 降级(模板) · {summary}"
                output_payload["output_summary"] = summary
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
                    langsmith_run_id=langsmith_run_id,
                    decision_meta={"degraded": degradations} if degradations else {},
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
