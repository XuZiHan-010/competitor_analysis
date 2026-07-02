from services.observability import _redact_payload, langsmith_enabled
from settings import Settings


def test_langsmith_requires_both_switch_and_credential() -> None:
    assert (
        langsmith_enabled(Settings(langchain_tracing_v2=False, langchain_api_key="placeholder"))
        is False
    )
    assert langsmith_enabled(Settings(langchain_tracing_v2=True, langchain_api_key=None)) is False
    assert (
        langsmith_enabled(Settings(langchain_tracing_v2=True, langchain_api_key="placeholder"))
        is True
    )


def test_langsmith_redaction_reaches_nested_sensitive_text() -> None:
    payload = {
        "survey": {
            "participants": [
                {
                    "email": "person@example.com",
                    "phone": "13800138000",
                    "quote": "Contact me at person@example.com",
                }
            ]
        }
    }

    redacted = _redact_payload(payload)
    participant = redacted["survey"]["participants"][0]

    assert "person@example.com" not in str(redacted)
    assert "13800138000" not in str(redacted)
    assert participant["email"] != payload["survey"]["participants"][0]["email"]
