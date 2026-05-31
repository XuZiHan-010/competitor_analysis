import json
from pathlib import Path
from typing import Any
from uuid import UUID

from schemas.demo import DemoReplayBundle, DemoReplaySnapshotResponse
from services.runs.manager import RunManager


class DemoReplayUnavailableError(RuntimeError):
    pass


FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "mocks" / "demo"


def load_demo_replay_bundle() -> DemoReplayBundle:
    scope = _load_object("scope")
    trace = _load_list("trace")
    report = _load_object("report")
    sources = _load_list("sources")
    demo_id = str(scope.get("task_id") or report.get("task_id") or "demo_replay")
    return DemoReplayBundle(
        demo_id=demo_id,
        scope=scope,
        trace=trace,
        report=report,
        sources=sources,
    )


async def build_demo_replay_snapshot(
    run_manager: RunManager,
    *,
    task_id: UUID,
    run_id: UUID,
    write_to_fixture: bool = False,
    fixture_root: Path = FIXTURE_ROOT,
) -> DemoReplaySnapshotResponse:
    scope_contract = run_manager.get_scope_contract(task_id)
    report = await run_manager.get_report(task_id)
    timeline = await run_manager.get_timeline(run_id)
    if scope_contract is None:
        raise DemoReplayUnavailableError("scope contract is not available for this task")
    if report is None:
        raise DemoReplayUnavailableError("report is not available for this task")
    if not timeline:
        raise DemoReplayUnavailableError("timeline is not available for this run")

    scope = _sanitize_payload(scope_contract.model_dump(mode="json"))
    report_payload = _sanitize_payload(report.model_dump(mode="json"))
    trace = [_sanitize_payload(item.model_dump(mode="json")) for item in timeline]
    sources = [_sanitize_payload(item.model_dump(mode="json")) for item in report.sources]
    bundle = DemoReplayBundle(
        demo_id=str(task_id),
        source="generated_from_completed_run",
        scope=scope,
        trace=trace,
        report=report_payload,
        sources=sources,
    )
    if not write_to_fixture:
        return DemoReplaySnapshotResponse(bundle=bundle)

    fixture_root.mkdir(parents=True, exist_ok=True)
    files = {
        "scope.json": bundle.scope,
        "trace.json": bundle.trace,
        "report.json": bundle.report,
        "sources.json": bundle.sources,
    }
    written_files: list[str] = []
    for filename, payload in files.items():
        path = fixture_root / filename
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written_files.append(str(path))
    return DemoReplaySnapshotResponse(
        bundle=bundle,
        written=True,
        fixture_root=str(fixture_root),
        files=written_files,
    )


def _load_object(name: str) -> dict[str, Any]:
    payload = _load_json(name)
    if not isinstance(payload, dict):
        raise DemoReplayUnavailableError(f"{name}.json must contain an object")
    return payload


def _load_list(name: str) -> list[dict[str, Any]]:
    payload = _load_json(name)
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise DemoReplayUnavailableError(f"{name}.json must contain a list of objects")
    return payload


def _load_json(name: str) -> Any:
    path = FIXTURE_ROOT / f"{name}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DemoReplayUnavailableError(f"missing demo fixture: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DemoReplayUnavailableError(f"invalid demo fixture JSON: {path}") from exc


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        source_type = value.get("source_type")
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            lower_key = str(key).lower()
            if lower_key in {
                "raw_content",
                "api_key",
                "token",
                "access_token",
                "password",
                "secret",
                "smtp_password",
            }:
                sanitized[key] = "[redacted]"
            elif key == "content" and source_type == "user_uploaded_primary":
                sanitized[key] = "[redacted user-uploaded evidence]"
            else:
                sanitized[key] = _sanitize_payload(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    return value
