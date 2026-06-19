"""Scrub credentials out of strings before they get logged or persisted.

Provider errors are the main offender: SerpApi puts the API key in the request
URL, so an httpx ``HTTPStatusError`` stringifies to a URL containing
``?api_key=<real key>``. That string flows into ``ToolError.error_content`` and
gets written to ``agent_traces`` in the DB — a red-line secret leak (AGENTS.md
§一.1). Redact at every boundary that records external error text.
"""

import re

# Matches `api_key=value`, `token=value`, etc. in URLs/query strings and the
# JSON form `"api_key": "value"`. Value runs until a delimiter (& # space " , })
# so we never swallow surrounding structure.
_SECRET_KEYS = r"(?:api[_-]?key|access[_-]?token|token|secret|password|passwd|pwd)"
_QUERY_PATTERN = re.compile(rf"(?i)({_SECRET_KEYS})=([^&#\s\"'<>]+)")
_JSON_PATTERN = re.compile(rf"(?i)(\"{_SECRET_KEYS}\"\s*:\s*\")([^\"]+)(\")")

_REDACTED = "***REDACTED***"


def redact_secrets(text: str) -> str:
    """Replace secret values (api_key, token, password, …) with a placeholder."""
    redacted = _QUERY_PATTERN.sub(rf"\1={_REDACTED}", text)
    return _JSON_PATTERN.sub(rf"\1{_REDACTED}\3", redacted)
