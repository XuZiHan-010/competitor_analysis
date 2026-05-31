"""Per-node LLM token usage capture.

``LLMClient`` records real provider-reported token counts into a context-local
accumulator; ``traced_node`` opens a capture around each agent node and reads the
aggregated total back out. This keeps the ``complete_text`` / ``complete_json``
return types unchanged while letting a node that issues several LLM calls report
the true summed usage instead of a payload-size estimate.
"""

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass
class _UsageAccumulator:
    tokens_in: int = 0
    tokens_out: int = 0
    calls: int = 0


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
