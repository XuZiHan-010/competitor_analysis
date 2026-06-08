import asyncio
import json
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any, Literal, TypeVar, cast

import structlog
from openai import AsyncOpenAI

from services.llm.usage import record_langsmith_run_id, record_usage
from services.observability import get_langsmith_client, langsmith_enabled
from settings import Settings

logger = structlog.get_logger(__name__)

LLMRole = Literal["system", "user", "assistant"]
Provider = Literal["openai", "deepseek", "gemini"]

T = TypeVar("T")
_JSON_MAX_ATTEMPTS = 3

_TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
_TRANSIENT_NAME_HINTS = (
    "servererror",
    "ratelimit",
    "serviceunavailable",
    "unavailable",
    "overloaded",
    "timeout",
    "apiconnection",
)


def _is_transient(exc: BaseException) -> bool:
    """Whether a provider error is worth retrying (overload / rate limit / network).

    Gemini raises ``ServerError`` (with a 503 ``code``), OpenAI/DeepSeek raise
    ``APIStatusError`` (with ``status_code``); we treat timeouts and connection
    drops as transient too. Anything else (e.g. 400 bad request) is permanent.
    """
    if isinstance(exc, asyncio.TimeoutError | TimeoutError):
        return True
    status = getattr(exc, "status_code", None)
    if not isinstance(status, int):
        status = getattr(exc, "code", None)
    if isinstance(status, int) and status in _TRANSIENT_STATUS:
        return True
    name = type(exc).__name__.lower()
    return any(hint in name for hint in _TRANSIENT_NAME_HINTS)


def _capture_run_id() -> None:
    """Record the live LangSmith run id into the per-node usage capture.

    Only valid while executing inside a traced context (``traceable``); that is
    why every provider call below is routed through ``_traced_llm_call``.
    """
    with suppress(Exception):
        from langsmith.run_helpers import get_current_run_tree

        run_tree = get_current_run_tree()
        if run_tree is not None:
            record_langsmith_run_id(str(run_tree.id))


class LLMClient:
    def __init__(
        self,
        settings: Settings,
        *,
        max_attempts: int = 3,
        retry_base_delay_s: float = 0.5,
        call_timeout_s: float = 60.0,
    ) -> None:
        self._settings = settings
        self._max_attempts = max(1, max_attempts)
        self._retry_base_delay_s = retry_base_delay_s
        self._call_timeout_s = call_timeout_s

    async def _call_with_retries(self, call: Callable[[], Awaitable[T]]) -> T:
        """Run a provider call with a per-attempt timeout and exponential backoff
        on transient errors, so a single 503/429/timeout doesn't degrade the node."""
        delay = self._retry_base_delay_s
        for attempt in range(self._max_attempts):
            try:
                return await asyncio.wait_for(call(), timeout=self._call_timeout_s)
            except Exception as exc:
                if attempt == self._max_attempts - 1 or not _is_transient(exc):
                    raise
                logger.warning(
                    "llm_call_transient_retry",
                    attempt=attempt + 1,
                    error_type=type(exc).__name__,
                )
                await asyncio.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable: retry loop exited without returning")

    @property
    def enabled(self) -> bool:
        if self._settings.mock_llm:
            return False
        return any(
            [
                self._settings.openai_api_key,
                self._settings.deepseek_api_key,
                self._settings.gemini_api_key,
            ]
        )

    def _openai_client(self, provider: Literal["openai", "deepseek"]) -> AsyncOpenAI:
        if provider == "openai":
            if not self._settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI calls")
            client = AsyncOpenAI(api_key=self._settings.openai_api_key)
        else:
            if not self._settings.deepseek_api_key:
                raise RuntimeError("DEEPSEEK_API_KEY is required for DeepSeek calls")
            client = AsyncOpenAI(
                api_key=self._settings.deepseek_api_key,
                base_url="https://api.deepseek.com/v1",
            )
        return client

    async def _traced_llm_call(
        self,
        *,
        name: str,
        payload: dict[str, Any],
        call: Callable[[], Awaitable[T]],
        process_outputs: Callable[[Any], dict[str, Any]] | None = None,
    ) -> T:
        """Run a provider call, wrapping it in a LangSmith ``traceable`` span when
        tracing is on so the run id can be captured from inside the live context."""
        if not langsmith_enabled(self._settings):
            return await self._call_with_retries(call)

        from langsmith import traceable

        async def _inner(_payload: dict[str, Any]) -> T:
            _capture_run_id()
            return await self._call_with_retries(call)

        traced = traceable(
            run_type="llm",
            name=name,
            client=get_langsmith_client(),
            process_outputs=process_outputs,
        )(_inner)
        return await traced(payload)

    async def complete_text(
        self,
        *,
        provider: Provider,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        if provider == "gemini":
            return await self._gemini_complete(
                model=model, messages=messages, temperature=temperature, json_mode=False
            )
        client = self._openai_client(provider)
        completions = cast(Any, client.chat.completions)
        response = await self._traced_llm_call(
            name=provider,
            payload={"model": model, "messages": messages},
            call=lambda: completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            ),
        )
        self._record_openai_usage(response)
        return response.choices[0].message.content or ""

    async def complete_json(
        self,
        *,
        provider: Provider,
        model: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        guarded_messages = _messages_with_json_guard(provider, messages)
        last_error: Exception | None = None
        for _ in range(_JSON_MAX_ATTEMPTS):
            try:
                content = await self._complete_json_text(
                    provider=provider,
                    model=model,
                    messages=guarded_messages,
                )
                if not content.strip():
                    raise ValueError("empty JSON response")
                payload = json.loads(content)
                if not isinstance(payload, dict):
                    raise ValueError("JSON response must be an object")
                return payload
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
        raise RuntimeError(
            f"{provider} model {model} returned invalid JSON after "
            f"{_JSON_MAX_ATTEMPTS} attempts: {type(last_error).__name__}: {last_error}"
        ) from last_error

    async def _complete_json_text(
        self,
        *,
        provider: Provider,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        if provider == "gemini":
            return await self._gemini_complete(
                model=model,
                messages=messages,
                temperature=0.2,
                json_mode=True,
            )
        client = self._openai_client(provider)
        completions = cast(Any, client.chat.completions)
        response = await self._traced_llm_call(
            name=provider,
            payload={"model": model, "messages": messages},
            call=lambda: completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            ),
        )
        self._record_openai_usage(response)
        return response.choices[0].message.content or ""

    async def _gemini_complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        json_mode: bool,
    ) -> str:
        if not self._settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini calls")
        from google import genai
        from google.genai import types

        client = cast(Any, genai).Client(api_key=self._settings.gemini_api_key)
        system_instruction = "\n".join(
            message["content"] for message in messages if message["role"] == "system"
        )
        contents = [message["content"] for message in messages if message["role"] != "system"]
        config = cast(Any, types).GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction or None,
            response_mime_type="application/json" if json_mode else None,
        )
        response = await self._traced_llm_call(
            name="gemini",
            payload={"model": model, "messages": messages, "json_mode": json_mode},
            call=lambda: client.aio.models.generate_content(
                model=model, contents=contents, config=config
            ),
            process_outputs=_summarize_gemini_trace_output,
        )
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            record_usage(
                int(getattr(usage, "prompt_token_count", 0) or 0),
                int(getattr(usage, "candidates_token_count", 0) or 0),
            )
        return response.text or ""

    def _record_openai_usage(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is not None:
            record_usage(
                int(getattr(usage, "prompt_tokens", 0) or 0),
                int(getattr(usage, "completion_tokens", 0) or 0),
            )


def _summarize_gemini_trace_output(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage_metadata", None)
    return {
        "text_length": len(getattr(response, "text", "") or ""),
        "prompt_tokens": int(getattr(usage, "prompt_token_count", 0) or 0)
        if usage is not None
        else 0,
        "completion_tokens": int(getattr(usage, "candidates_token_count", 0) or 0)
        if usage is not None
        else 0,
    }


def _messages_with_json_guard(
    provider: Provider,
    messages: list[dict[str, str]],
) -> list[dict[str, str]]:
    if provider != "deepseek":
        return messages
    guard = (
        'Return a valid JSON object only. Do not use Markdown fences. Example: {"ok": true}. '
        "If information is unavailable, return an empty array/object for that field rather "
        "than placeholder text."
    )
    return [*messages, {"role": "system", "content": guard}]
