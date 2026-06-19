"""One-off diagnostic for the "report renders but every section is empty" bug.

Reads only — never writes. Pulls the persisted truth for one task so we can tell
*why* the structured fields came out empty:

  A. Collector gathered thin / invalid / single-type sources -> Analyst correctly
     left fields empty (low 信源类型 / 来源支撑率 point here), or
  B. Collector gathered good sources but the Analyst node still emitted empty
     structured JSON (prompt / model / source-filter problem), or
  C. DeepSeek truncated or timed out and the half/empty JSON was accepted as valid
     (tokens_out pinned at the cap, latency near the 150s ceiling).

Usage:
    cd backend && python scripts/diagnose_empty_report.py [--task-id <uuid>]

DATABASE_URL is read from settings/.env (never hardcoded) per AGENTS.md red line.
"""

import argparse
import asyncio
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import UUID

# Allow `python scripts/diagnose_empty_report.py` from the backend/ dir.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from db import models  # noqa: E402
from db.session import create_engine, create_sessionmaker  # noqa: E402

# The run from the reported screenshot; override with --task-id for other runs.
_DEFAULT_TASK_ID = "3ef07e2e-280b-41a1-a634-9b728da2ff6b"

_CORE_DIM_HINTS = ("feature", "pric", "persona", "swot")


def _hr(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def _len(value: Any) -> int:
    return len(value) if hasattr(value, "__len__") else 0


def _swot_quadrant_counts(swot: Any) -> dict[str, int]:
    swot = swot if isinstance(swot, dict) else {}
    return {
        quad: _len(swot.get(quad))
        for quad in ("strengths", "weaknesses", "opportunities", "threats")
    }


async def _diagnose(task_id: UUID) -> None:
    engine = create_engine()
    sessionmaker = create_sessionmaker(engine)
    try:
        async with sessionmaker() as session:
            await _report_sources(session, task_id)
            await _report_profiles(session, task_id)
            await _report_analyst_traces(session, task_id)
            await _report_runs(session, task_id)
    finally:
        await engine.dispose()


async def _report_sources(session: Any, task_id: UUID) -> None:
    _hr("source_citations (Collector 实际收了什么)")
    rows = (
        await session.execute(
            select(models.SourceCitation).where(models.SourceCitation.task_id == task_id)
        )
    ).scalars().all()
    if not rows:
        print("⚠️  没有任何 source_citations —— Collector 几乎没收到东西（强烈指向支线 A）。")
        return

    by_category = Counter(r.category for r in rows)
    by_type = Counter(r.type for r in rows)
    by_provider = Counter(r.provider for r in rows)
    invalid = sum(1 for r in rows if not r.valid)
    print(f"总数: {len(rows)} | 无效(valid=false): {invalid}")
    print(f"category 分布: {dict(by_category)}  (信源类型覆盖 = 命中类别数/5)")
    print(f"type 分布:     {dict(by_type)}")
    print(f"provider 分布: {dict(by_provider)}")
    print("前若干条标题:")
    for r in rows[:10]:
        raw_len = len(r.raw_content or "")
        print(f"  [{r.category}/{r.type}/valid={r.valid}] raw={raw_len}b  {r.title[:80]}")


async def _report_profiles(session: Any, task_id: UUID) -> None:
    _hr("competitor_profiles (落库的结构化字段填充情况)")
    rows = (
        await session.execute(
            select(models.CompetitorProfile).where(models.CompetitorProfile.task_id == task_id)
        )
    ).scalars().all()
    if not rows:
        print("⚠️  没有 competitor_profiles。")
        return
    for p in rows:
        ft_rows = (p.feature_tree or {}).get("rows") if isinstance(p.feature_tree, dict) else None
        tiers = (p.pricing or {}).get("tiers") if isinstance(p.pricing, dict) else None
        personas = p.user_personas if isinstance(p.user_personas, list) else (p.user_personas or {})
        print(
            f"- {p.competitor_name}: "
            f"feature_tree.rows={_len(ft_rows)} | pricing.tiers={_len(tiers)} | "
            f"personas={_len(personas)} | swot={_swot_quadrant_counts(p.swot)}"
        )


async def _report_analyst_traces(session: Any, task_id: UUID) -> None:
    _hr("agent_traces — AnalystAgent (最新一次 run)")
    latest_run = (
        await session.execute(
            select(models.TaskRun)
            .where(models.TaskRun.task_id == task_id)
            .order_by(models.TaskRun.started_at.desc().nullslast())
        )
    ).scalars().first()
    if latest_run is None:
        print("⚠️  没有 task_runs。")
        return
    print(
        f"task_run={latest_run.id} status={latest_run.status} "
        f"retry_count={latest_run.retry_count}"
    )

    traces = (
        await session.execute(
            select(models.AgentTrace)
            .where(
                models.AgentTrace.task_run_id == latest_run.id,
                models.AgentTrace.agent_name == "AnalystAgent",
            )
            .order_by(models.AgentTrace.sequence_no)
        )
    ).scalars().all()
    if not traces:
        print("⚠️  这次 run 没有 AnalystAgent trace —— Analyst 没跑或没记录。")
        return
    for t in traces:
        out = t.output_payload if isinstance(t.output_payload, dict) else {}
        degraded = (t.decision_meta or {}).get("degraded")
        print(
            f"\n  seq={t.sequence_no} status={t.status} "
            f"tokens_in={t.tokens_in} tokens_out={t.tokens_out} latency_ms={t.latency_ms}"
        )
        print(f"  output_summary: {out.get('output_summary')}")
        if degraded:
            print(f"  ⚠️ degraded(模板兜底): {degraded}")
        # The node returns a tuple, so the full extraction lands in output_payload['value']
        # as a repr string. Print a window so empty feature_tree/pricing/swot is visible.
        value_repr = out.get("value")
        if isinstance(value_repr, str):
            print(f"  value repr (首 1500 字):\n    {value_repr[:1500]}")
        if t.tokens_out >= 8192:
            print("  ⚠️ tokens_out 触顶 8192 —— 可能是 JSON 被截断（支线 C：截断被当合法空）。")
        if t.latency_ms >= 145000:
            print("  ⚠️ latency 接近 150s 上限 —— 可能超时（支线 C）。")


async def _report_runs(session: Any, task_id: UUID) -> None:
    _hr("task_runs.error_summary")
    rows = (
        await session.execute(
            select(models.TaskRun)
            .where(models.TaskRun.task_id == task_id)
            .order_by(models.TaskRun.started_at.desc().nullslast())
        )
    ).scalars().all()
    for r in rows:
        print(f"- run={r.id} status={r.status} error_summary={r.error_summary}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", default=_DEFAULT_TASK_ID)
    args = parser.parse_args()
    # psycopg's async driver can't run on Windows' default ProactorEventLoop.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(_diagnose(UUID(args.task_id)))


if __name__ == "__main__":
    main()
