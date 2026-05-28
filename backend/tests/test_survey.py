from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from services.survey import redact_sensitive_text


def test_redact_sensitive_text() -> None:
    text = "姓名：张三 phone 138-0000-0000 email eric@example.com"
    redacted = redact_sensitive_text(text)
    assert "张三" not in redacted
    assert "138-0000-0000" not in redacted
    assert "eric@example.com" not in redacted


def test_upload_survey_redacts_and_counts_evidence() -> None:
    client = TestClient(app)
    task_id = uuid4()
    response = client.post(
        f"/api/tasks/{task_id}/survey/upload",
        json={
            "kind": "interview_record",
            "content": "姓名：李四\n喜欢功能矩阵\n电话 13900000000",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["parsed_evidence_count"] == 3
    assert all(item["source_type"] == "user_uploaded_primary" for item in data["evidence"])
    assert "李四" not in str(data)
    assert "13900000000" not in str(data)
