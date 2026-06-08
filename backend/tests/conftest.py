import os
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

os.environ["MOCK_LLM"] = "true"
os.environ["DATABASE_URL"] = ""
os.environ["REDIS_URL"] = ""
os.environ["JWT_SECRET"] = "test-secret"
# Keep tests deterministic and offline: never emit LangSmith traces, regardless
# of the developer's .env (env vars take precedence over the .env file).
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from services.auth import JwtService  # noqa: E402
from services.storage import store  # noqa: E402
from settings import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def reset_in_memory_state() -> Iterator[None]:
    from api.dependencies import run_manager

    store.scoping_drafts.clear()
    store.task_scopes.clear()
    store.task_owner.clear()
    store.task_reports.clear()
    store.survey_uploads.clear()
    store.traces_by_run.clear()
    run_manager._runs.clear()
    yield


@pytest.fixture
def auth_client_factory() -> Callable[[str], TestClient]:
    def factory(email: str = "eric@example.com") -> TestClient:
        client = TestClient(app)
        token = JwtService(get_settings().jwt_secret or "test-secret").issue(email)
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client

    return factory
