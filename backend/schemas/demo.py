from typing import Any

from pydantic import BaseModel, Field


class DemoReplayBundle(BaseModel):
    demo_id: str
    demo_mode: bool = True
    route_scope: str = "demo_only"
    source: str = "frontend_static_fixture"
    scope: dict[str, Any]
    trace: list[dict[str, Any]]
    report: dict[str, Any]
    sources: list[dict[str, Any]]
    export_formats: list[str] = Field(default_factory=lambda: ["markdown", "pdf"])


class DemoReplaySnapshotResponse(BaseModel):
    bundle: DemoReplayBundle
    written: bool = False
    fixture_root: str | None = None
    files: list[str] = Field(default_factory=list)
