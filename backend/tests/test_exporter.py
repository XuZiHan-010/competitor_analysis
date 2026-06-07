from uuid import uuid4

import pytest

from schemas.report import Report, ReportClaim, ReportMetrics
from schemas.source import SourceCitation
from services.exporter import export_markdown, render_report_markdown, render_report_pdf
from services.report_html import build_report_html


def _report(**overrides: object) -> Report:
    base: dict = {
        "task_id": uuid4(),
        "structured_content": _structured_content(),
        "markdown_content": "# 占位标题",
        "sources": [
            SourceCitation(
                id="src_1",
                type="official",
                url="https://example.com/a",
                title="来源 A",
                snippet="中文来源片段",
                provider="test",
                dimension_id="core.feature_tree",
            )
        ],
        "claims": [
            ReportClaim(
                claim_path="claims[1]",
                claim_text="Notion 的模板生态领先竞品。",
                layer="core",
                field_type="free_text",
                source_ids=["src_1"],
                generating_agent="WriterAgent",
            )
        ],
        "metrics": ReportMetrics(
            field_coverage_rate=1.0,
            citation_coverage_rate=1.0,
            manual_correction_rate=0.0,
        ),
    }
    base.update(overrides)
    return Report(**base)


def test_build_report_html_renders_ui_like_sections_without_field_leaks() -> None:
    html = build_report_html(_report())

    assert "<table>" in html
    assert "功能树" in html
    assert "定价模型" in html
    assert "用户画像" in html
    assert "SWOT" in html
    assert "生态强" in html
    assert "Notion 的模板生态领先竞品。" in html
    assert "中文来源片段" in html
    assert "{'text'" not in html
    assert "source_ids:" not in html
    assert "background: #ffffff" in html
    assert "#f8f5eb" not in html
    assert "#1b4c64" not in html


def test_build_report_html_escapes_llm_text() -> None:
    report = _report(
        structured_content={
            **_structured_content(),
            "title": "A <script>alert(1)</script>",
        }
    )

    html = build_report_html(report)

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_render_markdown_uses_clean_tables_and_no_internal_fields() -> None:
    md = render_report_markdown(_report())

    assert "# Notion vs Lark" in md
    assert "## 功能对比" in md
    assert "| 竞品 | 方案 | 价格 | 亮点 |" in md
    assert "生态强" in md
    assert "Notion 的模板生态领先竞品。" in md
    assert "{'text'" not in md
    assert "source_ids:" not in md
    assert "占位标题" not in md


def test_export_markdown_has_body_not_just_title() -> None:
    body = export_markdown(_report()).decode("utf-8")

    assert "中文摘要" in body
    assert "Notion 的模板生态领先竞品。" in body
    assert "占位标题" not in body


@pytest.mark.asyncio
async def test_render_report_pdf_uses_playwright_when_browser_available() -> None:
    try:
        pdf = await render_report_pdf(_report())
    except Exception as exc:
        _skip_if_playwright_browser_missing(exc)
        raise

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1_000


def _skip_if_playwright_browser_missing(exc: Exception) -> None:
    message = str(exc)
    missing_browser_signals = (
        "Executable doesn't exist",
        "playwright install",
        "Host system is missing dependencies",
    )
    if any(signal in message for signal in missing_browser_signals):
        pytest.skip("Playwright Chromium is not installed in this environment")


def _structured_content() -> dict[str, object]:
    return {
        "title": "Notion vs Lark",
        "subtitle": "基于 2 个竞品的深度分析",
        "summary": "中文摘要",
        "competitors": ["Notion", "Lark"],
        "feature_tree": {
            "rows": [
                {
                    "feature": "实时协作",
                    "description": "多人同时编辑",
                    "cells": [
                        {"competitor": "Notion", "status": "supported", "note": "稳定"},
                        {"competitor": "Lark", "status": "partial", "note": "需验证"},
                    ],
                    "source_ids": ["src_1"],
                }
            ]
        },
        "pricing": {
            "tiers": [
                {
                    "competitor": "Notion",
                    "tier": "Plus",
                    "price": "$10",
                    "highlights": ["团队协作", "模板"],
                    "source_ids": ["src_1"],
                }
            ]
        },
        "user_personas": {
            "personas": [
                {
                    "competitor": "Notion",
                    "label": "知识工作者",
                    "size": "majority",
                    "needs": ["整理知识"],
                    "pain_points": ["迁移成本"],
                    "evidence": "访谈摘要",
                    "source_ids": ["src_1"],
                }
            ]
        },
        "swot": {
            "blocks": [
                {
                    "competitor": "Notion",
                    "strengths": [{"text": "生态强", "source_ids": ["src_1"]}],
                    "weaknesses": [{"text": "离线弱", "source_ids": []}],
                    "opportunities": ["AI 工作流"],
                    "threats": [{"text": "竞品迭代快", "source_ids": []}],
                }
            ]
        },
        "extensions": [
            {
                "dimension_id": "ext.user_voice",
                "title": "用户声音",
                "intent": "聚合公开评论",
                "summary": "Notion 用户喜欢模板生态。",
                "bullets": [
                    {
                        "competitor": "Notion",
                        "points": ["模板生态丰富"],
                        "source_ids": ["src_1"],
                    }
                ],
            }
        ],
        "cross_analysis": {
            "differentiation_summary": "Notion 更偏知识库，Lark 更偏协作套件。",
        },
        "survey": [
            {
                "competitor_name": "Notion",
                "insights": [{"point": "用户重视模板复用", "confidence": "high"}],
            }
        ],
    }
