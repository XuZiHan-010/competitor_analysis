import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from services.agents.wrappers import ToolError, run_tool_safely
from services.search.hybrid import SearchUnavailableError
from services.search.providers import PermanentProviderError


def _run(coro_factory: Callable[[], Awaitable[Any]]) -> Any:
    return asyncio.run(run_tool_safely("web_search", coro_factory))


def test_run_tool_safely_flags_permanent_provider_error() -> None:
    async def call() -> list[str]:
        raise PermanentProviderError("quota exhausted")

    result = _run(call)

    assert isinstance(result, ToolError)
    assert result.error_kind == "permanent"


def test_run_tool_safely_flags_permanent_search_unavailable() -> None:
    async def call() -> list[str]:
        raise SearchUnavailableError("all providers exhausted", permanent=True)

    result = _run(call)

    assert isinstance(result, ToolError)
    assert result.error_kind == "permanent"


def test_run_tool_safely_marks_transient_failures_as_transient() -> None:
    async def call() -> list[str]:
        raise TimeoutError("flaky network")

    result = _run(call)

    assert isinstance(result, ToolError)
    assert result.error_kind == "transient"


def test_run_tool_safely_transient_for_non_permanent_search_error() -> None:
    async def call() -> list[str]:
        raise SearchUnavailableError("empty results")

    result = _run(call)

    assert isinstance(result, ToolError)
    assert result.error_kind == "transient"
