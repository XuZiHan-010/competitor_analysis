import argparse
import asyncio
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

from schemas.report import Report
from services.report_html import (
    CitationIndex,
    JsonMapping,
    as_list,
    as_mapping,
    build_report_html,
    extension_sections,
    feature_competitors,
    list_text,
    markdown_cell,
    personas,
    pricing_tiers,
    report_structured_content,
    status_with_note,
    survey_results,
    swot_blocks,
    swot_item_entries,
    text_value,
)


class PdfRenderError(RuntimeError):
    """Raised when no Chromium-compatible browser can render the report PDF."""


def export_markdown(report: Report) -> bytes:
    return render_report_markdown(report).encode("utf-8")


async def render_report_pdf(report: Report) -> bytes:
    html = build_report_html(report)
    return await _render_pdf_subprocess(html)


def render_report_markdown(report: Report) -> str:
    """Serialize structured_content + claims into readable Markdown.

    structured_content is the export source of truth because WriterAgent may
    store a placeholder markdown_content for historical reports.
    """
    sc = report_structured_content(report)
    cite = CitationIndex(report.sources)
    lines: list[str] = [f"# {text_value(sc.get('title')) or '竞品分析报告'}"]

    subtitle = text_value(sc.get("subtitle"))
    if subtitle:
        lines.append(f"_{subtitle}_")
    summary = text_value(sc.get("summary"))
    if summary:
        lines += ["", summary]

    _append_feature_matrix(lines, sc, cite)
    _append_pricing(lines, sc, cite)
    _append_personas(lines, sc, cite)
    _append_swot(lines, sc, cite)
    _append_extensions(lines, sc, cite)
    _append_cross_analysis(lines, sc)
    _append_survey(lines, sc)
    _append_claims(lines, report, cite)
    _append_sources(lines, cite)

    return "\n".join(lines) + "\n"


async def _render_pdf_subprocess(html: str) -> bytes:
    with TemporaryDirectory(prefix="report-pdf-") as tmpdir:
        html_path = Path(tmpdir) / "report.html"
        pdf_path = Path(tmpdir) / "report.pdf"
        html_path.write_text(html, encoding="utf-8")

        try:
            completed = await asyncio.to_thread(
                subprocess.run,
                [
                    sys.executable,
                    "-m",
                    "services.exporter",
                    "--render-pdf-child",
                    str(html_path),
                    str(pdf_path),
                ],
                capture_output=True,
                check=False,
                timeout=30,
                cwd=Path(__file__).resolve().parents[1],
            )
        except subprocess.TimeoutExpired as exc:
            raise PdfRenderError("PDF 渲染子进程超时（>30s）。") from exc
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout).decode(
                "utf-8", errors="replace"
            ).strip()
            raise PdfRenderError(message or "PDF 渲染子进程失败。")
        if not pdf_path.exists():
            raise PdfRenderError("PDF 渲染子进程未生成输出文件。")
        return pdf_path.read_bytes()


def _render_pdf_sync(html: str) -> bytes:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    if sys.platform == "win32":
        asyncio_module = cast(Any, asyncio)
        asyncio.set_event_loop_policy(
            asyncio_module.WindowsProactorEventLoopPolicy()
        )

    with sync_playwright() as playwright:
        browser = _launch_pdf_browser(playwright, PlaywrightError)
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="load", timeout=15_000)
            page.emulate_media(media="print")
            return page.pdf(
                format="A4",
                print_background=True,
                margin={
                    "top": "18mm",
                    "right": "16mm",
                    "bottom": "18mm",
                    "left": "16mm",
                },
                prefer_css_page_size=True,
            )
        finally:
            browser.close()


def _render_pdf_child(html_path: Path, pdf_path: Path) -> int:
    try:
        pdf_path.write_bytes(_render_pdf_sync(html_path.read_text(encoding="utf-8")))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-pdf-child", action="store_true")
    parser.add_argument("html_path", nargs="?")
    parser.add_argument("pdf_path", nargs="?")
    args = parser.parse_args(argv)

    if args.render_pdf_child:
        if not args.html_path or not args.pdf_path:
            parser.error("--render-pdf-child requires html_path and pdf_path")
        return _render_pdf_child(Path(args.html_path), Path(args.pdf_path))
    parser.error("unsupported exporter command")
    return 2


def _launch_pdf_browser(playwright: Any, error_type: type[Exception]) -> Any:
    attempts: tuple[dict[str, Any], ...] = (
        {},
        {"channel": "chrome"},
        {"channel": "msedge"},
    )
    last_error: Exception | None = None
    for kwargs in attempts:
        try:
            return playwright.chromium.launch(headless=True, **kwargs)
        except error_type as exc:
            last_error = exc
            message = str(exc).lower()
            if (
                "executable doesn't exist" not in message
                and "not found" not in message
                and "not installed" not in message
            ):
                raise
    hint = (
        "PDF 渲染需要 Chromium，但未找到可用浏览器。"
        "请在 backend 目录运行 `python -m playwright install chromium`。"
    )
    raise PdfRenderError(hint) from last_error


def _append_feature_matrix(lines: list[str], sc: JsonMapping, cite: CitationIndex) -> None:
    feature_tree = as_mapping(sc.get("feature_tree"))
    rows = as_list(feature_tree.get("rows"))
    if not rows:
        return

    competitors = feature_competitors(sc, rows)
    lines += ["", "## 功能对比"]
    _append_table(lines, ["功能", *competitors])
    for row_value in rows:
        row = as_mapping(row_value)
        cells_by_competitor = {
            text_value(as_mapping(cell).get("competitor")): as_mapping(cell)
            for cell in as_list(row.get("cells"))
        }
        feature = text_value(row.get("feature"))
        description = text_value(row.get("description"))
        feature_cell = f"{feature} - {description}" if description else feature
        feature_cell += cite.markdown_marker(row.get("source_ids"))
        values = [
            feature_cell,
            *[
                status_with_note(cells_by_competitor.get(competitor, {}))
                for competitor in competitors
            ],
        ]
        _append_table_row(lines, values)


def _append_pricing(lines: list[str], sc: JsonMapping, cite: CitationIndex) -> None:
    tiers = pricing_tiers(sc)
    if not tiers:
        return

    lines += ["", "## 定价模型"]
    _append_table(lines, ["竞品", "方案", "价格", "亮点"])
    for tier in tiers:
        _append_table_row(
            lines,
            [
                text_value(tier.get("competitor")),
                text_value(tier.get("tier")),
                text_value(tier.get("price")),
                list_text(tier.get("highlights")) + cite.markdown_marker(tier.get("source_ids")),
            ],
        )


def _append_personas(lines: list[str], sc: JsonMapping, cite: CitationIndex) -> None:
    items = personas(sc)
    if not items:
        return

    lines += ["", "## 用户画像"]
    _append_table(lines, ["竞品", "画像", "规模", "需求", "痛点", "证据"])
    for persona in items:
        _append_table_row(
            lines,
            [
                text_value(persona.get("competitor")),
                text_value(persona.get("label")),
                text_value(persona.get("size")),
                list_text(persona.get("needs")),
                list_text(persona.get("pain_points")),
                text_value(persona.get("evidence"))
                + cite.markdown_marker(persona.get("source_ids")),
            ],
        )


def _append_swot(lines: list[str], sc: JsonMapping, cite: CitationIndex) -> None:
    blocks = swot_blocks(sc)
    if not blocks:
        return

    lines += ["", "## SWOT"]
    labels = (
        ("strengths", "优势"),
        ("weaknesses", "劣势"),
        ("opportunities", "机会"),
        ("threats", "威胁"),
    )
    for block in blocks:
        competitor = text_value(block.get("competitor"))
        if competitor:
            lines.append(f"### {competitor}")
        for key, label in labels:
            entries = swot_item_entries(block, key)
            items = [
                f"{item}{cite.markdown_marker(source_ids)}"
                for item, source_ids in entries
            ]
            if items:
                lines.append(f"- {label}: {'；'.join(items)}")


def _append_extensions(lines: list[str], sc: JsonMapping, cite: CitationIndex) -> None:
    extensions = extension_sections(sc)
    if not extensions:
        return

    lines += ["", "## 扩展维度"]
    for ext in extensions:
        title = text_value(ext.get("title")) or text_value(ext.get("dimension_id"))
        if title:
            lines.append(f"### {title}")
        if text_value(ext.get("intent")):
            lines.append(f"_意图：{text_value(ext.get('intent'))}_")
        if text_value(ext.get("summary")):
            lines.append(text_value(ext.get("summary")))
        for bullet_value in as_list(ext.get("bullets")):
            bullet = as_mapping(bullet_value)
            competitor = text_value(bullet.get("competitor"))
            points = [text_value(point) for point in as_list(bullet.get("points"))]
            rendered = "；".join(point for point in points if point)
            rendered += cite.markdown_marker(bullet.get("source_ids"))
            if competitor or rendered:
                lines.append(f"- {competitor}: {rendered}" if competitor else f"- {rendered}")


def _append_cross_analysis(lines: list[str], sc: JsonMapping) -> None:
    cross = as_mapping(sc.get("cross_analysis"))
    summary = text_value(cross.get("differentiation_summary"))
    if summary:
        lines += ["", "## 交叉分析", summary]


def _append_survey(lines: list[str], sc: JsonMapping) -> None:
    insight_lines: list[str] = []
    for survey in survey_results(sc):
        competitor = text_value(survey.get("competitor_name"))
        for insight_value in as_list(survey.get("insights")):
            insight = as_mapping(insight_value)
            point = text_value(insight.get("point"))
            if point:
                insight_lines.append(f"- {competitor}: {point}" if competitor else f"- {point}")
    if insight_lines:
        lines += ["", "## 调研洞察", *insight_lines]


def _append_claims(lines: list[str], report: Report, cite: CitationIndex) -> None:
    claim_lines = [
        f"- {claim.claim_text.strip()}{cite.markdown_marker(claim.source_ids)}"
        for claim in report.claims
        if claim.claim_text.strip()
    ]
    if claim_lines:
        lines += ["", "## 关键结论", *claim_lines]


def _append_sources(lines: list[str], cite: CitationIndex) -> None:
    groups = cite.ordered_groups()
    if not groups:
        return

    lines += ["", "### 来源"]
    for title, sources in groups:
        lines += ["", f"#### {title}"]
        for number, source in sources:
            source_title = text_value(source.title) or text_value(source.url) or source.id
            url = text_value(source.url)
            label = f"[S{number}]"
            linked_title = f"[{source_title}]({url})" if url else source_title
            lines.append(f"{number}. {label} {linked_title} — `{source.id}`")


def _append_table(lines: list[str], headers: Iterable[object]) -> None:
    header_values = [markdown_cell(value) for value in headers]
    lines.append("| " + " | ".join(header_values) + " |")
    lines.append("| " + " | ".join("---" for _ in header_values) + " |")


def _append_table_row(lines: list[str], values: Iterable[object]) -> None:
    lines.append("| " + " | ".join(markdown_cell(value) for value in values) + " |")


if __name__ == "__main__":
    raise SystemExit(main())
