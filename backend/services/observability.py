import os
from functools import lru_cache
from typing import Any

import structlog

from services.survey import redact_sensitive_text
from settings import Settings, get_settings

logger = structlog.get_logger(__name__)


def langsmith_enabled(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.langchain_tracing_v2 and settings.langchain_api_key)


def configure_langsmith(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if not langsmith_enabled(settings):
        # Surface *why* tracing is off so a missing trace is never silently
        # mistaken for a broken integration. Never log the api key itself.
        reason = (
            "LANGCHAIN_TRACING_V2 is false"
            if not settings.langchain_tracing_v2
            else "LANGCHAIN_API_KEY is empty"
        )
        logger.info("langsmith_tracing_disabled", reason=reason)
        return
    _export_langsmith_env(settings)
    get_langsmith_client.cache_clear()
    get_langsmith_client()
    logger.info("langsmith_tracing_enabled", project=settings.langchain_project)


@lru_cache
def get_langsmith_client() -> Any | None:
    settings = get_settings()
    if not langsmith_enabled(settings):
        return None
    _export_langsmith_env(settings)
    from langsmith import Client

    return Client(
        api_key=settings.langchain_api_key,
        hide_inputs=_redact_payload,
        hide_outputs=_redact_payload,
    )


def _export_langsmith_env(settings: Settings) -> None:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key or ""
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langchain_api_key or ""
    os.environ["LANGSMITH_PROJECT"] = settings.langchain_project


def langsmith_extra() -> dict[str, Any]:
    client = get_langsmith_client()
    return {"langsmith_extra": {"client": client}} if client is not None else {}


def _redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return _redact_value(payload)


def _redact_value(value: Any, depth: int = 10) -> Any:
    if depth <= 0:
        return value
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, list):
        return [_redact_value(item, depth - 1) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item, depth - 1) for item in value)
    if isinstance(value, dict):
        return {key: _redact_value(item, depth - 1) for key, item in value.items()}
    return value
