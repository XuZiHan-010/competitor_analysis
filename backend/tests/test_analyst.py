import asyncio
from typing import Any

from agents.analyst import AnalystAgent, _canonical_feature_status
from graph.state import RawCollectionResult, StructuredCompetitorProfile
from schemas.source import SourceCitation


def _source(sid: str) -> SourceCitation:
    return SourceCitation(
        id=sid,
        type="app_review",
        category="user_feedback",
        title="Review",
        snippet="Evidence.",
        provider="tavily",
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
        agent._enrich_cross_matrix(cross, _profiles(), _raw_collections(), llm)  # type: ignore[arg-type]
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
        agent._enrich_cross_matrix(cross, _profiles(), _raw_collections(), llm)  # type: ignore[arg-type]
    )
    assert _cell_status(enriched, "Group Chat", "B") == "unknown"


def test_cross_fill_keeps_unknown_when_llm_fails() -> None:
    agent = AnalystAgent()
    cross = agent._build_cross_analysis(_profiles())

    llm = _FakeLLM(error=RuntimeError("deepseek down"))
    enriched = asyncio.run(
        agent._enrich_cross_matrix(cross, _profiles(), _raw_collections(), llm)  # type: ignore[arg-type]
    )
    assert _cell_status(enriched, "Group Chat", "B") == "unknown"
