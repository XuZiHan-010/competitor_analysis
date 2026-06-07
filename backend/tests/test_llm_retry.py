import asyncio

import pytest

from services.llm.client import LLMClient, _is_transient
from settings import get_settings


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


def test_is_transient_detects_gemini_server_error_and_timeout() -> None:
    class ServerError(Exception):
        ...

    assert _is_transient(ServerError("503 UNAVAILABLE"))
    assert _is_transient(TimeoutError())
    assert _is_transient(_Transient())
    assert not _is_transient(_Permanent())
