from services.redaction import redact_secrets


def test_redacts_api_key_in_url() -> None:
    raw = (
        "serpapi: Client error '429 Too Many Requests' for url "
        "'https://serpapi.com/search.json?engine=google&q=foo&api_key=abc123secret&num=10'"
    )
    cleaned = redact_secrets(raw)
    assert "abc123secret" not in cleaned
    assert "api_key=***REDACTED***" in cleaned
    # Non-secret query params are preserved.
    assert "engine=google" in cleaned
    assert "num=10" in cleaned


def test_redacts_json_token_field() -> None:
    raw = '{"query": "x", "api_key": "live_KEY_123", "token": "t0ken"}'
    cleaned = redact_secrets(raw)
    assert "live_KEY_123" not in cleaned
    assert "t0ken" not in cleaned
    assert cleaned.count("***REDACTED***") == 2


def test_leaves_clean_text_untouched() -> None:
    raw = "search(飞书 pricing plans): empty results"
    assert redact_secrets(raw) == raw
