from collections.abc import Awaitable, Callable
from typing import Literal, TypeVar

from pydantic import BaseModel

from services.redaction import redact_secrets
from services.search.providers import PermanentProviderError


class ToolError(BaseModel):
    tool_name: str
    error_content: str
    error_kind: Literal["transient", "permanent"] = "transient"


T = TypeVar("T")


async def run_tool_safely(tool_name: str, call: Callable[[], Awaitable[T]]) -> T | ToolError:
    try:
        return await call()
    except Exception as exc:
        # Provider errors stringify to request URLs that may carry an api_key
        # (e.g. SerpApi); scrub before this text is logged or persisted to traces.
        permanent = isinstance(exc, PermanentProviderError) or bool(
            getattr(exc, "permanent", False)
        )
        return ToolError(
            tool_name=tool_name,
            error_content=redact_secrets(str(exc)),
            error_kind="permanent" if permanent else "transient",
        )
