from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class StreamEvent(BaseModel):
    id: int
    run_id: str
    event: Literal[
        "run.started",
        "node.started",
        "node.succeeded",
        "node.failed",
        "collector.degraded",
        "qa.blocker",
        "run.succeeded",
        "run.failed",
        "__heartbeat__",
    ]
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
