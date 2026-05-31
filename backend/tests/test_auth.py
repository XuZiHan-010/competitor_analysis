from collections.abc import Iterator
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

from main import app
from settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_email_code_login_and_me() -> None:
    client = TestClient(app)
    send_response = client.post("/api/auth/send-code", json={"email": "eric@example.com"})
    assert send_response.status_code == 200
    code = send_response.json()["dev_code"]
    assert code

    verify_response = client.post(
        "/api/auth/verify",
        json={"email": "eric@example.com", "code": code},
    )
    assert verify_response.status_code == 200
    assert "strata_session" in verify_response.cookies
    token = verify_response.json()["access_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "eric@example.com"

    cookie_me_response = client.get("/api/auth/me")
    assert cookie_me_response.status_code == 200
    assert cookie_me_response.json()["email"] == "eric@example.com"

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204


def test_production_send_code_requires_smtp_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM_EMAIL", raising=False)
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.post("/api/auth/send-code", json={"email": "eric@example.com"})

    assert response.status_code == 500
    assert "SMTP_HOST" in response.json()["detail"]


def test_production_send_code_uses_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    sent_messages: list[EmailMessage] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            self.host = host
            self.port = port
            self.timeout = timeout

        def starttls(self) -> None:
            return None

        def send_message(self, message: EmailMessage) -> None:
            sent_messages.append(message)

        def quit(self) -> None:
            return None

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr("services.auth.smtplib.SMTP", FakeSMTP)
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.post("/api/auth/send-code", json={"email": "eric@example.com"})

    assert response.status_code == 200
    assert response.json() == {"sent": True, "dev_code": None}
    assert len(sent_messages) == 1
    assert sent_messages[0]["To"] == "eric@example.com"
    assert "验证码" in sent_messages[0].get_content()
