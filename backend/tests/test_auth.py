from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from main import app
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
