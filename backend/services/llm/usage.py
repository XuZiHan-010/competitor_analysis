"""Per-node LLM token usage capture.

``LLMClient`` records real provider-reported token counts into a context-local
accumulator; ``traced_node`` opens a capture around each agent node and reads the
aggregated total back out. This keeps the ``complete_text`` / ``complete_json``
return types unchanged while letting a node that issues several LLM calls report
the true summed usage instead of a payload-size estimate.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass, field


@dataclass
class _UsageAccumulator:
    tokens_in: int = 0
    tokens_out: int = 0
    calls: int = 0
    langsmith_run_id: str | None = None
    degradations: list[str] = field(default_factory=list)


_current: ContextVar[_UsageAccumulator | None] = ContextVar("llm_usage", default=None)


def start_capture() -> Token[_UsageAccumulator | None]:
    return _current.set(_UsageAccumulator())


def reset_capture(token: Token[_UsageAccumulator | None]) -> None:
    _current.reset(token)


def record_usage(tokens_in: int, tokens_out: int) -> None:
    accumulator = _current.get()
    if accumulator is not None:
        accumulator.tokens_in += tokens_in
        accumulator.tokens_out += tokens_out
        accumulator.calls += 1


def collected_usage() -> tuple[int, int] | None:
    """Return (tokens_in, tokens_out) if any real usage was recorded, else None."""
    accumulator = _current.get()
    if accumulator is None or accumulator.calls == 0:
        return None
    return accumulator.tokens_in, accumulator.tokens_out


def record_langsmith_run_id(run_id: str) -> None:
    """Stash the LangSmith run id of this node's LLM call (first call wins).

    Must be called from *inside* the traced call context (where the run tree is
    live); ``traced_node`` reads it back via ``collected_langsmith_run_id`` to
    link the persisted trace to its LangSmith run.
    """
    accumulator = _current.get()
    if accumulator is not None and accumulator.langsmith_run_id is None:
        accumulator.langsmith_run_id = run_id


def collected_langsmith_run_id() -> str | None:
    accumulator = _current.get()
    return accumulator.langsmith_run_id if accumulator is not None else None


def record_degradation(reason: str) -> None:
    """Mark that this node silently fell back to a template after an LLM/parse failure.

    ``traced_node`` reads these back via ``collected_degradations`` so the persisted
    trace shows the node ran degraded instead of reporting a clean success — the
    failure was previously invisible because ``run()`` swallows the exception and
    returns the fallback result.
    """
    accumulator = _current.get()
    if accumulator is not None:
        accumulator.degradations.append(reason)


def collected_degradations() -> list[str]:
    accumulator = _current.get()
    return list(accumulator.degradations) if accumulator is not None else []
