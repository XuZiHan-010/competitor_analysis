from fastapi.testclient import TestClient

from main import app


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
    token = verify_response.json()["access_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "eric@example.com"
