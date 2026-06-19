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
Provider = Literal["openai", "deepseek"]

T = TypeVar("T")
_JSON_MAX_ATTEMPTS = 3
_JSON_LOG_SNIPPET_CHARS = 180

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


def provider_for_model(model: str) -> Provider:
    lowered = model.lower()
    if lowered.startswith("deepseek"):
        return "deepseek"
    return "openai"


def _is_transient(exc: BaseException) -> bool:
    """Whether a provider error is worth retrying (overload / rate limit / network)."""
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


def _extract_first_json_object(content: str) -> str | None:
    start = content.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(content)):
        char = content[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]
    return None


def _parse_json_object(content: str) -> dict[str, Any]:
    if not content.strip():
        raise ValueError("empty JSON response")

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        candidate = _extract_first_json_object(content)
        if candidate is None or candidate == content.strip():
            raise exc
        payload = json.loads(candidate)

    if not isinstance(payload, dict):
        raise ValueError("JSON response must be an object")
    return payload


def _json_content_snippets(content: str) -> dict[str, str | int]:
    return {
        "response_length": len(content),
        "response_head": content[:_JSON_LOG_SNIPPET_CHARS],
        "response_tail": content[-_JSON_LOG_SNIPPET_CHARS:],
    }


class LLMClient:
    def __init__(
        self,
        settings: Settings,
        *,
        max_attempts: int = 3,
        retry_base_delay_s: float = 0.5,
        # deepseek-v4-pro generates large structured JSON at ~50 tok/s; a single
        # core-profile extraction (~3.5k out tokens) runs ~70s, so the old 60s
        # ceiling timed the node out. 150s fits a full profile with headroom.
        call_timeout_s: float = 150.0,
        # Guardrail against runaway generation (the model can emit up to its 384K
        # output ceiling). Kept generous so it never truncates a real profile —
        # a tight cap returns empty/partial JSON and triggers spurious retries.
        max_output_tokens: int = 8192,
    ) -> None:
        self._settings = settings
        self._max_attempts = max(1, max_attempts)
        self._retry_base_delay_s = retry_base_delay_s
        self._call_timeout_s = call_timeout_s
        self._max_output_tokens = max_output_tokens

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
            ]
        )

    def supports_provider(self, provider: Provider) -> bool:
        if provider == "openai":
            return bool(self._settings.openai_api_key)
        return bool(self._settings.deepseek_api_key)

    def _openai_client(self, provider: Literal["openai", "deepseek"]) -> AsyncOpenAI:
        # max_retries=0 disables the SDK's own hidden retries so that
        # _call_with_retries stays the single retry layer (PRD §五.Y "最多 3 次");
        # timeout matches the per-attempt wait_for so a cancelled call releases
        # the httpx connection cleanly instead of hanging in aiter_bytes.
        if provider == "openai":
            if not self._settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI calls")
            client = AsyncOpenAI(
                api_key=self._settings.openai_api_key,
                max_retries=0,
                timeout=self._call_timeout_s,
            )
        else:
            if not self._settings.deepseek_api_key:
                raise RuntimeError("DEEPSEEK_API_KEY is required for DeepSeek calls")
            client = AsyncOpenAI(
                api_key=self._settings.deepseek_api_key,
                base_url="https://api.deepseek.com/v1",
                max_retries=0,
                timeout=self._call_timeout_s,
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
        client = self._openai_client(provider)
        completions = cast(Any, client.chat.completions)
        response = await self._traced_llm_call(
            name=provider,
            payload={"model": model, "messages": messages},
            call=lambda: completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=self._max_output_tokens,
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
        repair_invalid: bool = True,
        expected_shape: str | None = None,
    ) -> dict[str, Any]:
        guarded_messages = _messages_with_json_guard(provider, messages)
        last_error: Exception | None = None
        for attempt in range(_JSON_MAX_ATTEMPTS):
            content = ""
            try:
                content = await self._complete_json_text(
                    provider=provider,
                    model=model,
                    messages=guarded_messages,
                )
                return _parse_json_object(content)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "llm_json_parse_failed",
                    provider=provider,
                    model=model,
                    attempt=attempt + 1,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    **_json_content_snippets(content),
                )
                if not repair_invalid or not content.strip():
                    continue
                try:
                    repaired = await self._repair_json_text(
                        provider=provider,
                        model=model,
                        invalid_content=content,
                        expected_shape=expected_shape,
                    )
                    return _parse_json_object(repaired)
                except (json.JSONDecodeError, ValueError) as repair_exc:
                    last_error = repair_exc
                    logger.warning(
                        "llm_json_repair_failed",
                        provider=provider,
                        model=model,
                        attempt=attempt + 1,
                        error_type=type(repair_exc).__name__,
                        error_message=str(repair_exc),
                        **_json_content_snippets(content),
                    )
        raise RuntimeError(
            f"{provider} model {model} returned invalid JSON after "
            f"{_JSON_MAX_ATTEMPTS} attempts: {type(last_error).__name__}: {last_error}"
        ) from last_error

    async def _repair_json_text(
        self,
        *,
        provider: Provider,
        model: str,
        invalid_content: str,
        expected_shape: str | None,
    ) -> str:
        shape_instruction = (
            f"Expected root JSON object shape: {expected_shape}"
            if expected_shape
            else "Return one valid JSON object."
        )
        return await self._complete_json_text(
            provider=provider,
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Repair malformed JSON syntax only. Return valid JSON and nothing else. "
                        "Do not add facts, remove facts, summarize, translate, rename fields, "
                        "or change any field meaning. If a string is unterminated, close it with "
                        "the smallest valid edit. "
                        + shape_instruction
                    ),
                },
                {
                    "role": "user",
                    "content": "Malformed JSON to repair:\n" + invalid_content,
                },
            ],
        )

    async def _complete_json_text(
        self,
        *,
        provider: Provider,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
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
                max_tokens=self._max_output_tokens,
            ),
        )
        self._record_openai_usage(response)
        return response.choices[0].message.content or ""

    def _record_openai_usage(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is not None:
            record_usage(
                int(getattr(usage, "prompt_tokens", 0) or 0),
                int(getattr(usage, "completion_tokens", 0) or 0),
            )


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
