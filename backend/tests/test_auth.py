from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from main import app
from services.auth import JwtService
from settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_login_and_me() -> None:
    client = TestClient(app)
    login_response = client.post("/api/auth/login", json={"email": "eric@example.com"})
    assert login_response.status_code == 200
    assert "strata_session" in login_response.cookies
    token = login_response.json()["access_token"]
    assert token

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "eric@example.com"

    cookie_me_response = client.get("/api/auth/me")
    assert cookie_me_response.status_code == 200
    assert cookie_me_response.json()["email"] == "eric@example.com"

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204


def test_jwt_rejects_expired_tampered_and_wrong_signature_tokens() -> None:
    service = JwtService("test-signing-secret")
    expired = service.issue("eric@example.com", expires_delta=timedelta(seconds=-1))
    valid = service.issue("eric@example.com")
    header, payload, signature = valid.split(".")

    with pytest.raises(ValueError, match="expired"):
        service.verify(expired)
    with pytest.raises(ValueError, match="signature"):
        service.verify(f"{header}.{payload}.{signature[:-1]}x")
    with pytest.raises(ValueError, match="signature"):
        JwtService("different-signing-secret").verify(valid)


def test_jwt_requires_configured_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        JwtService("")

    monkeypatch.setenv("JWT_SECRET", "")
    get_settings.cache_clear()
    response = TestClient(app).get(
        "/api/auth/me",
        headers={"Authorization": "Bearer placeholder"},
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "JWT_SECRET is not configured"
