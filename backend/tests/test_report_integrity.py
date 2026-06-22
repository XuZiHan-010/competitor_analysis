import pytest

from schemas.report import ReportClaim
from schemas.source import SourceCitation
from services.report_integrity import (
    assert_report_sources_resolvable,
    prune_report_sources_to_references,
    source_ids_from_payload,
)


def _source(source_id: str, *, url: str | None = None) -> SourceCitation:
    return SourceCitation(
        id=source_id,
        type="media",
        category="media",
        url=url,
        title=f"Source {source_id}",
        snippet="Evidence.",
        provider="test",
    )


def _claim(source_ids: list[str]) -> ReportClaim:
    return ReportClaim(
        claim_path="feature_tree.rows[0]",
        claim_text="Feature evidence.",
        layer="core",
        field_type="structured",
        source_ids=source_ids,
        generating_agent="WriterAgent",
    )


def test_source_ids_from_payload_reads_nested_source_ids() -> None:
    payload = {
        "feature_tree": {"rows": [{"source_ids": ["src_a", 42]}]},
        "swot": {"blocks": [{"strengths": [{"source_ids": ["src_b"]}]}]},
    }

    assert source_ids_from_payload(payload) == {"src_a", "src_b"}


def test_prune_report_sources_keeps_only_referenced_and_remaps_duplicate_urls() -> None:
    sources = [
        _source("src_a", url="https://example.com/pricing/"),
        _source("src_b", url="https://example.com/pricing"),
        _source("src_unused", url="https://example.com/unused"),
    ]
    claims = [_claim(["src_a", "src_b"])]
    structured_content = {
        "feature_tree": {
            "rows": [
                {"feature": "Pricing", "source_ids": ["src_b"]},
            ]
        }
    }

    pruned_sources, remapped_claims, remapped_content, _ = prune_report_sources_to_references(
        sources=sources,
        claims=claims,
        structured_content=structured_content,
    )

    assert [source.id for source in pruned_sources] == ["src_a"]
    assert remapped_claims[0].source_ids == ["src_a"]
    assert remapped_content["feature_tree"]["rows"][0]["source_ids"] == ["src_a"]
    assert structured_content["feature_tree"]["rows"][0]["source_ids"] == ["src_b"]
    assert_report_sources_resolvable(
        sources=pruned_sources,
        claims=remapped_claims,
        structured_content=remapped_content,
    )


def test_prune_report_sources_keeps_unresolved_references_visible() -> None:
    pruned_sources, remapped_claims, remapped_content, _ = prune_report_sources_to_references(
        sources=[_source("src_a")],
        claims=[_claim(["missing"])],
        structured_content={},
    )

    assert pruned_sources == []
    assert remapped_claims[0].source_ids == ["missing"]
    # assert_report_sources_resolvable now warns + records degradation instead of raising,
    # so unresolved refs are survivable — the run produces a report with a degradation flag.
    assert_report_sources_resolvable(
        sources=pruned_sources,
        claims=remapped_claims,
        structured_content=remapped_content,
    )  # must not raise