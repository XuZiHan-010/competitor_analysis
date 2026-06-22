from uuid import uuid4

from schemas.report import Report, ReportMetrics
from schemas.source import SourceCitation
from services.report_html import build_report_html


def _source(source_id: str) -> SourceCitation:
    return SourceCitation(
        id=source_id,
        type="media",
        category="media",
        url=f"https://example.com/{source_id}",
        title=f"Source {source_id}",
        snippet="Evidence.",
        provider="test",
    )


def _metrics() -> ReportMetrics:
    return ReportMetrics(
        field_coverage_rate=1.0,
        citation_coverage_rate=1.0,
        manual_correction_rate=0.0,
    )


def test_sources_list_only_includes_visible_citations() -> None:
    # src_visible is written verbatim into a rendered cell note; src_hidden_only lives only in a
    # hidden source_ids array and is never surfaced to the reader.
    structured_content = {
        "title": "竞品分析报告",
        "feature_tree": {
            "rows": [
                {
                    "feature": "可视化工作流",
                    "source_ids": ["src_hidden_only"],
                    "cells": [
                        {
                            "competitor": "飞书",
                            "status": "supported",
                            "note": "飞书提供可视化工作流（src_visible）。",
                            "source_ids": ["src_hidden_only"],
                        }
                    ],
                }
            ]
        },
    }
    report = Report(
        task_id=uuid4(),
        structured_content=structured_content,
        markdown_content="",
        sources=[_source("src_visible"), _source("src_hidden_only")],
        claims=[],
        metrics=_metrics(),
    )

    html = build_report_html(report)

    assert "src_visible" in html
    assert "src_hidden_only" not in html


def _report_with_gaps(*, data_gap_competitors: list[str], competitors: list[str]) -> Report:
    structured_content = {
        "title": "竞品分析报告",
        "competitors": competitors,
        "data_gaps": [
            {"competitor": name, "reason": "fetch_error"} for name in data_gap_competitors
        ],
    }
    return Report(
        task_id=uuid4(),
        structured_content=structured_content,
        markdown_content="",
        sources=[],
        claims=[],
        metrics=_metrics(),
        qa_status="issues",
    )


def test_quality_banner_grades_partial_when_some_competitors_have_data() -> None:
    report = _report_with_gaps(
        data_gap_competitors=["飞书", "钉钉"],
        competitors=["飞书", "钉钉", "企业微信"],
    )

    html = build_report_html(report)

    assert "部分可用" in html
    assert "草稿 / 待复核" not in html
    assert "quality-warning partial" in html
    assert "企业微信 已采集到有效数据" in html


def test_quality_banner_stays_draft_when_all_competitors_failed() -> None:
    report = _report_with_gaps(
        data_gap_competitors=["飞书", "钉钉", "企业微信"],
        competitors=["飞书", "钉钉", "企业微信"],
    )

    html = build_report_html(report)

    assert "草稿 / 待复核" in html
    assert "部分可用" not in html


def test_quality_banner_absent_when_passed() -> None:
    report = _report_with_gaps(data_gap_competitors=[], competitors=["飞书"])
    report.qa_status = "passed"

    html = build_report_html(report)

    # The .quality-warning class always lives in the stylesheet; assert the banner
    # section text itself is absent for a passing report.
    assert "草稿 / 待复核" not in html
    assert "部分可用" not in html


def test_sources_section_omitted_when_no_visible_citations() -> None:
    report = Report(
        task_id=uuid4(),
        structured_content={"title": "竞品分析报告"},
        markdown_content="",
        sources=[_source("src_unused")],
        claims=[],
        metrics=_metrics(),
    )

    html = build_report_html(report)

    assert "src_unused" not in html
    # The sources chapter (class="chapter sources") is omitted entirely when nothing is cited.
    assert "chapter sources" not in html
