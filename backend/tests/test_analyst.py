import asyncio
from math import isfinite
from typing import Any

from agents.analyst import AnalystAgent, _canonical_feature_status
from graph.state import RawCollectionResult, StructuredCompetitorProfile, WorkflowState
from schemas.scope import CompetitorCandidate, ScopeDimension, TaskScopeContract
from schemas.source import SourceCitation
from services.report_integrity import assert_report_sources_resolvable, source_ids_from_payload


def _source(sid: str, dimension_id: str | None = None) -> SourceCitation:
    return SourceCitation(
        id=sid,
        type="app_review",
        category="user_feedback",
        title="Review",
        snippet="Evidence.",
        provider="tavily",
        dimension_id=dimension_id,
    )


def _profiles() -> dict[str, StructuredCompetitorProfile]:
    """A documents "Group Chat"; B documents nothing → B's cell starts unknown."""
    a = StructuredCompetitorProfile(
        competitor_name="A",
        feature_tree={
            "rows": [
                {
                    "feature": "Group Chat",
                    "cells": [{"competitor": "A", "status": "supported", "note": "Has it"}],
                    "source_ids": ["src_a_001"],
                }
            ]
        },
        pricing={},
        user_personas=[],
        swot={},
        source_ids=["src_a_001"],
    )
    b = StructuredCompetitorProfile(
        competitor_name="B",
        feature_tree={"rows": []},
        pricing={},
        user_personas=[],
        swot={},
        source_ids=["src_b_001"],
    )
    return {"A": a, "B": b}


def _raw_collections() -> dict[str, RawCollectionResult]:
    return {
        "A": RawCollectionResult(competitor_name="A", sources=[_source("src_a_001")]),
        "B": RawCollectionResult(competitor_name="B", sources=[_source("src_b_001")]),
    }


class _FakeLLM:
    """Returns a fixed payload for every complete_json call (or raises)."""

    def __init__(self, payload: dict[str, Any] | None = None, *, error: Exception | None = None):
        self._payload = payload or {}
        self._error = error

    async def complete_json(self, **_: Any) -> dict[str, Any]:
        if self._error is not None:
            raise self._error
        return self._payload


def _cell_status(cross: Any, feature: str, competitor: str) -> str:
    for row in cross.feature_matrix["rows"]:
        if row["feature"] == feature:
            for cell in row["cells"]:
                if cell["competitor"] == competitor:
                    return _canonical_feature_status(cell["status"])
    raise AssertionError(f"cell not found: {feature}/{competitor}")


def test_cross_fill_applies_classification_backed_by_competitor_sources() -> None:
    agent = AnalystAgent()
    cross = agent._build_cross_analysis(_profiles())
    assert _cell_status(cross, "Group Chat", "B") == "unknown"

    llm = _FakeLLM(
        {
            "features": [
                {
                    "feature": "Group Chat",
                    "status": "supported",
                    "note": "B supports group chat",
                    "source_ids": ["src_b_001"],
                }
            ]
        }
    )
    enriched = asyncio.run(
        agent._enrich_cross_matrix(cross, _profiles(), _raw_collections(), llm, "zh")  # type: ignore[arg-type]
    )

    assert _cell_status(enriched, "Group Chat", "B") == "supported"
    row = next(r for r in enriched.feature_matrix["rows"] if r["feature"] == "Group Chat")
    cell = next(c for c in row["cells"] if c["competitor"] == "B")
    assert cell["note"] == "B supports group chat"
    assert "src_b_001" in row["source_ids"]


def test_cross_fill_rejects_classification_without_valid_evidence() -> None:
    agent = AnalystAgent()
    cross = agent._build_cross_analysis(_profiles())

    # Cites a source id that does NOT belong to competitor B → must be ignored.
    llm = _FakeLLM(
        {
            "features": [
                {
                    "feature": "Group Chat",
                    "status": "supported",
                    "note": "guessed",
                    "source_ids": ["src_x_999"],
                }
            ]
        }
    )
    enriched = asyncio.run(
        agent._enrich_cross_matrix(cross, _profiles(), _raw_collections(), llm, "zh")  # type: ignore[arg-type]
    )
    assert _cell_status(enriched, "Group Chat", "B") == "unknown"


def test_cross_fill_keeps_unknown_when_llm_fails() -> None:
    agent = AnalystAgent()
    cross = agent._build_cross_analysis(_profiles())

    llm = _FakeLLM(error=RuntimeError("deepseek down"))
    enriched = asyncio.run(
        agent._enrich_cross_matrix(cross, _profiles(), _raw_collections(), llm, "zh")  # type: ignore[arg-type]
    )
    assert _cell_status(enriched, "Group Chat", "B") == "unknown"


class _SequenceLLM:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self._payloads = payloads

    async def complete_json(self, **_: Any) -> dict[str, Any]:
        if not self._payloads:
            return {}
        return self._payloads.pop(0)


def test_extension_source_fallback_uses_dimension_sources_only() -> None:
    scope = TaskScopeContract(
        user_brief="Compare coding tools",
        intent_mode="list",
        competitors=[CompetitorCandidate(name="A", source="nl_extracted")],
        dimensions=[
            ScopeDimension(
                id="core.feature_tree",
                title="Feature tree",
                intent="Compare features",
                layer="core",
                order=1,
            ),
            ScopeDimension(
                id="ext.ecosystem",
                title="Ecosystem",
                intent="Compare ecosystem signals",
                layer="extension",
                order=5,
            ),
        ],
    )
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "A": RawCollectionResult(
                competitor_name="A",
                sources=[
                    _source("src_core", "core.feature_tree"),
                    _source("src_ext", "ext.ecosystem"),
                    _source("src_other", "ext.other"),
                ],
            )
        },
    )
    llm = _SequenceLLM(
        [
            {
                "feature_tree": {"rows": []},
                "pricing": {"tiers": []},
                "user_personas": [],
                "swot": {},
            },
            {"summary": "Ecosystem evidence", "bullets": ["Has marketplace"]},
        ]
    )

    _, extension_findings, _ = asyncio.run(AnalystAgent()._run_llm(state, llm))  # type: ignore[arg-type]

    assert len(extension_findings) == 1
    assert extension_findings[0].source_ids == ["src_ext"]


def test_run_llm_drops_hallucinated_nested_source_ids() -> None:
    """Nested source_ids the model invents must be stripped before they reach the
    Writer's integrity gate (the root cause of 'unresolved report source ids')."""
    scope = TaskScopeContract(
        user_brief="Compare coding tools",
        intent_mode="list",
        competitors=[CompetitorCandidate(name="A", source="nl_extracted")],
        dimensions=[
            ScopeDimension(
                id="core.feature_tree",
                title="Feature tree",
                intent="Compare features",
                layer="core",
                order=1,
            ),
        ],
    )
    state = WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "A": RawCollectionResult(
                competitor_name="A",
                sources=[_source("src_a_001", "core.feature_tree")],
            )
        },
    )
    llm = _FakeLLM(
        {
            "feature_tree": {
                "rows": [
                    {
                        "feature": "Group Chat",
                        "cells": [{"competitor": "A", "status": "supported", "note": "Has it"}],
                        "source_ids": ["src_a_001", "src_hallucinated_999"],
                    }
                ]
            },
            "pricing": {
                "tiers": [
                    {
                        "competitor": "A",
                        "tier": "Free",
                        "price": "$0",
                        "highlights": [],
                        "source_ids": ["src_ghost_000"],
                    }
                ]
            },
            "user_personas": [],
            "swot": {},
        }
    )

    profiles, _, cross = asyncio.run(AnalystAgent()._run_llm(state, llm))  # type: ignore[arg-type]
    assert cross is not None

    profile = profiles["A"]
    assert profile.feature_tree["rows"][0]["source_ids"] == ["src_a_001"]
    assert profile.pricing["tiers"][0]["source_ids"] == []
    assert "src_hallucinated_999" not in source_ids_from_payload(profile.model_dump(mode="json"))
    assert "src_ghost_000" not in source_ids_from_payload(cross.model_dump(mode="json"))

    # End to end: the cleaned content passes the Writer's integrity gate.
    assert_report_sources_resolvable(
        sources=[_source("src_a_001")],
        claims=[],
        structured_content={
            "feature_tree": profile.feature_tree,
            "pricing": profile.pricing,
            "cross_analysis": cross.model_dump(mode="json"),
        },
    )


def test_cross_analysis_builds_positioning_map_points() -> None:
    cross = AnalystAgent()._build_cross_analysis(_profiles())
    positioning_map = cross.positioning_map
    points = positioning_map["competitors"]

    assert positioning_map["x_axis"]
    assert positioning_map["y_axis"]
    assert {point["id"] for point in points} == {"A", "B"}
    for point in points:
        assert isfinite(point["x"])
        assert isfinite(point["y"])
        assert 0 <= point["x"] <= 100
        assert 0 <= point["y"] <= 100
