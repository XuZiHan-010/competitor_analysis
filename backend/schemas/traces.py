from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentTrace(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    task_run_id: UUID
    sequence_no: int
    agent_name: str
    node_name: str
    status: Literal["started", "succeeded", "failed", "skipped", "retried"]
    prompt: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    langsmith_run_id: str | None = None
    decision_meta: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
