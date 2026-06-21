import asyncio
from uuid import uuid4

from structlog.testing import capture_logs

from schemas.scope import CompetitorCandidate, ScopeDimension, TaskScopeContract
from services.runs.manager import RunManager
from services.storage import InMemoryStore
from services.streaming.bridge import InMemoryStreamBridge


def test_start_run_logs_only_enabled_frozen_scope_summary() -> None:
    scope = TaskScopeContract(
        user_brief="Compare AI coding tools",
        intent_mode="list",
        competitors=[CompetitorCandidate(name="Trae", source="nl_extracted")],
        dimensions=[
            ScopeDimension(
                id="core.feature_tree",
                title="Feature tree",
                intent="Compare features",
                layer="core",
                order=1,
            ),
            ScopeDimension(
                id="ext.keep",
                title="Usage scenarios",
                intent="Keep this dimension",
                layer="extension",
                order=5,
                source="ai_suggested",
            ),
            ScopeDimension(
                id="ext.deleted",
                title="Enterprise pricing strategy",
                intent="Deleted by user",
                layer="extension",
                order=6,
                enabled=False,
                source="ai_suggested",
            ),
        ],
    )
    manager = RunManager(InMemoryStore(), InMemoryStreamBridge())

    with capture_logs() as logs:
        asyncio.run(
            manager.start_run(
                scope,
                user_id=uuid4(),
                user_email="eric@example.com",
            )
        )

    frozen_logs = [entry for entry in logs if entry.get("event") == "task_scope_frozen"]
    assert len(frozen_logs) == 1
    logged = frozen_logs[0]
    logged_dimensions = logged["enabled_dimensions"]
    assert [dimension["id"] for dimension in logged_dimensions] == [
        "core.feature_tree",
        "ext.keep",
    ]
    all_dimensions = logged["all_dimensions"]
    assert [dimension["id"] for dimension in all_dimensions] == [
        "core.feature_tree",
        "ext.keep",
        "ext.deleted",
    ]
    assert all_dimensions[-1]["enabled"] is False
    assert logged["competitors"] == ["Trae"]
    assert "eric@example.com" not in str(logged)
    assert "secret" not in str(logged).lower()
    assert "key" not in str(logged).lower()