import asyncio

import pytest

from services.llm.client import LLMClient, _is_transient
from settings import Settings, get_settings


class _Transient(Exception):
    status_code = 503


class _Permanent(Exception):
    status_code = 400


def _client() -> LLMClient:
    return LLMClient(get_settings(), max_attempts=3, retry_base_delay_s=0.0)


def test_retries_transient_then_succeeds() -> None:
    calls = {"n": 0}

    async def call() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise _Transient("503 overloaded")
        return "ok"

    assert asyncio.run(_client()._call_with_retries(call)) == "ok"
    assert calls["n"] == 3


def test_permanent_error_not_retried() -> None:
    calls = {"n": 0}

    async def call() -> str:
        calls["n"] += 1
        raise _Permanent("400 bad request")

    with pytest.raises(_Permanent):
        asyncio.run(_client()._call_with_retries(call))
    assert calls["n"] == 1


def test_openai_client_disables_sdk_retries() -> None:
    """LLMClient must be the only retry layer (PRD §五.Y "最多 3 次"); the SDK's
    own hidden retries are disabled and its timeout aligned to call_timeout_s."""
    client = LLMClient(
        Settings(openai_api_key="sk-test", deepseek_api_key="sk-test"),
        call_timeout_s=150.0,
    )
    for provider in ("openai", "deepseek"):
        sdk = client._openai_client(provider)
        assert sdk.max_retries == 0
        assert sdk.timeout == 150.0


def test_is_transient_detects_gemini_server_error_and_timeout() -> None:
    class ServerError(Exception):
        ...

    assert _is_transient(ServerError("503 UNAVAILABLE"))
    assert _is_transient(TimeoutError())
    assert _is_transient(_Transient())
    assert not _is_transient(_Permanent())
