from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel


class ToolError(BaseModel):
    tool_name: str
    error_content: str


T = TypeVar("T")


async def run_tool_safely(tool_name: str, call: Callable[[], Awaitable[T]]) -> T | ToolError:
    try:
        return await call()
    except Exception as exc:
        return ToolError(tool_name=tool_name, error_content=str(exc))
