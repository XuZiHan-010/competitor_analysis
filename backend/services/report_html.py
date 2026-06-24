from collections.abc import Iterable, Mapping
from html import escape
from math import isfinite
from typing import Any

from schemas.report import Report
from schemas.source import SourceCitation

JsonMapping = Mapping[str, Any]


def build_report_html(report: Report) -> str:
    sc = report_structured_content(report)
    cite = CitationIndex(report.sources)
    title = text_value(sc.get("title")) or "竞品分析报告"
    subtitle = text_value(sc.get("subtitle"))
    summary = text_value(sc.get("summary"))
    created_at = report.created_at.strftime("%Y-%m-%d")
    extension_count = len(extension_sections(sc))

    pre_source_sections = [
        _masthead(title=title, subtitle=subtitle, summary=summary, created_at=created_at),
        _quality_status(report),
        _metrics(report),
        _data_gaps_banner(sc),
        _field_gaps_banner(sc),
        _feature_matrix(sc, cite),
        _pricing_table(sc, cite),
        _persona_cards(sc, cite),
        _swot_blocks(sc, cite),
        _extensions(sc, cite),
        _cross_analysis(sc, index=5 + extension_count),
        _survey_insights(sc, index=6 + extension_count),
        _claims(report, index=7 + extension_count),
    ]
    body_before = "\n".join(section for section in pre_source_sections if section)
    sources_section = _sources(cite, index=8 + extension_count)
    body = "\n".join(section for section in (body_before, sources_section) if section)
    return f"""<!doctype html>
<html lang="{escape(report.language)}">
<head>
  <meta charset="utf-8" />
  <title>{html_text(title)}</title>
  <style>{_STYLE}</style>
</head>
<body>
  <main class="report">
    {body}
  </main>
</body>
</html>
"""


def report_structured_content(report: Report) -> JsonMapping:
    return as_mapping(report.structured_content)


_TYPE_ABBREV = {
    "official": "官",
    "commercial": "商",
    "media": "媒",
    "user_feedback": "反",
    "tech_community": "技",
    "user_uploaded": "传",
    "published_survey": "调",
    "public_review": "公",
    "app_review": "评",
    "ai_simulated": "AI",
}

_FACTUAL_TYPES = {
    "official",
    "commercial",
    "media",
    "tech_community",
    "user_feedback",
    "user_uploaded",
}
_USER_VOICE_TYPES = {"app_review", "public_review", "published_survey"}


class CitationIndex:
    def __init__(self, sources: Iterable[SourceCitation]) -> None:
        self._groups = self._build_groups(list(sources))
        self._numbers: dict[str, int] = {}
        self._sources: dict[str, SourceCitation] = {}
        counter = 1
        for _, group_sources in self._groups:
            for source in group_sources:
                if source.id in self._numbers:
                    continue
                self._numbers[source.id] = counter
                self._sources[source.id] = source
                counter += 1

    def number(self, source_id: str) -> int | None:
        return self._numbers.get(source_id)

    def ordered_groups(self) -> list[tuple[str, list[tuple[int, SourceCitation]]]]:
        groups: list[tuple[str, list[tuple[int, SourceCitation]]]] = []
        for title, sources in self._groups:
            numbered = [
                (number, source)
                for source in sources
                if (number := self.number(source.id)) is not None
            ]
            if numbered:
                groups.append((title, numbered))
        return groups

    def html_marker(self, source_ids: Any) -> str:
        links = []
        for source_id in _source_id_values(source_ids):
            source = self._sources.get(source_id)
            number = self.number(source_id)
            if not source or number is None:
                continue
            type_abbrev = _TYPE_ABBREV.get(source.type, source.type[:2])
            links.append(
                f'<a class="cite" href="#{html_text(source.id)}" '
                f'title="{html_text(source.title)}">S{number}·{html_text(type_abbrev)}</a>'
            )
        if not links:
            return ""
        return f'<sup class="cites">{"".join(links)}</sup>'

    def markdown_marker(self, source_ids: Any) -> str:
        markers = [
            f"[S{number}]"
            for source_id in _source_id_values(source_ids)
            if (number := self.number(source_id)) is not None
        ]
        return "".join(markers)

    @staticmethod
    def _build_groups(
        sources: list[SourceCitation],
    ) -> list[tuple[str, list[SourceCitation]]]:
        factual = [
            source
            for source in sources
            if source.type in _FACTUAL_TYPES and not _is_simulated_source(source)
        ]
        user_voice = [source for source in sources if source.type in _USER_VOICE_TYPES]
        simulated = [source for source in sources if _is_simulated_source(source)]
        grouped_ids = {source.id for source in [*factual, *user_voice, *simulated]}
        other = [source for source in sources if source.id not in grouped_ids]
        return [
            ("报告正文来源", [*factual, *other]),
            ("用户声音来源", user_voice),
            ("模拟 / 兜底来源", simulated),
        ]


def _is_simulated_source(source: SourceCitation) -> bool:
    provider = source.provider.lower()
    return (
        source.type == "ai_simulated"
        or "fallback" in provider
        or "simulated" in provider
    )


def _source_id_values(value: Any) -> list[str]:
    raw_values = value if isinstance(value, list) else [value]
    seen: dict[str, None] = {}
    for raw in raw_values:
        source_id = text_value(raw)
        if source_id:
            seen.setdefault(source_id, None)
    return list(seen)


def as_mapping(value: Any) -> JsonMapping:
    return value if isinstance(value, Mapping) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        if "text" in value:
            return text_value(value.get("text"))
        if "point" in value:
            return text_value(value.get("point"))
        return ""
    if isinstance(value, list):
        return "、".join(item for item in (text_value(item) for item in value) if item)
    return str(value).strip()


def html_text(value: Any) -> str:
    return escape(text_value(value), quote=True)


def list_text(value: Any, separator: str = "、") -> str:
    if isinstance(value, list):
        return separator.join(item for item in (text_value(item) for item in value) if item)
    return text_value(value)


def swot_item_texts(block: JsonMapping, key: str) -> list[str]:
    return [text for text, _ in swot_item_entries(block, key)]


def swot_item_entries(block: JsonMapping, key: str) -> list[tuple[str, list[str]]]:
    entries: list[tuple[str, list[str]]] = []
    for item in as_list(block.get(key)):
        text = text_value(item)
        if text:
            entries.append((text, _source_id_values(as_mapping(item).get("source_ids"))))
    return entries


def feature_competitors(sc: JsonMapping, rows: list[Any]) -> list[str]:
    explicit = [text_value(item) for item in as_list(sc.get("competitors"))]
    competitors = [item for item in explicit if item]
    if competitors:
        return competitors

    seen: dict[str, None] = {}
    for row_value in rows:
        row = as_mapping(row_value)
        for cell_value in as_list(row.get("cells")):
            competitor = text_value(as_mapping(cell_value).get("competitor"))
            if competitor:
                seen.setdefault(competitor, None)
    return list(seen)


def status_with_note(cell: JsonMapping) -> str:
    status = text_value(cell.get("status")) or "unknown"
    note = text_value(cell.get("note"))
    return f"{status} - {note}" if note else status


def finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def pricing_tiers(sc: JsonMapping) -> list[JsonMapping]:
    return [as_mapping(tier) for tier in as_list(as_mapping(sc.get("pricing")).get("tiers"))]


def personas(sc: JsonMapping) -> list[JsonMapping]:
    return [
        as_mapping(persona)
        for persona in as_list(as_mapping(sc.get("user_personas")).get("personas"))
    ]


def swot_blocks(sc: JsonMapping) -> list[JsonMapping]:
    return [as_mapping(block) for block in as_list(as_mapping(sc.get("swot")).get("blocks"))]


def extension_sections(sc: JsonMapping) -> list[JsonMapping]:
    return [as_mapping(ext) for ext in as_list(sc.get("extensions"))]


def survey_results(sc: JsonMapping) -> list[JsonMapping]:
    return [as_mapping(survey) for survey in as_list(sc.get("survey"))]


def markdown_cell(value: Any) -> str:
    text = text_value(value).replace("\n", " ")
    return text.replace("|", "\\|")


def _masthead(*, title: str, subtitle: str, summary: str, created_at: str) -> str:
    subtitle_html = f'<p class="subtitle">{html_text(subtitle)}</p>' if subtitle else ""
    summary_html = f'<p class="summary">{html_text(summary)}</p>' if summary else ""
    return f"""
<header class="masthead">
  <p class="eyebrow">Report · {html_text(created_at)}</p>
  <h1>{html_text(title)}</h1>
  {subtitle_html}
  {summary_html}
</header>
"""


def _metrics(report: Report) -> str:
    metrics = report.metrics
    items = [
        ("字段覆盖", _percent(metrics.field_coverage_rate)),
        ("引用覆盖", _percent(metrics.citation_coverage_rate)),
        ("人工修正", _percent(metrics.manual_correction_rate)),
    ]
    if metrics.source_support_rate is not None:
        items.append(("来源支撑", _percent(metrics.source_support_rate)))
    badges = "\n".join(
        f'<span class="metric"><b>{html_text(value)}</b>{html_text(label)}</span>'
        for label, value in items
    )
    return f'<section class="metrics" aria-label="关键指标">{badges}</section>'


def _report_competitor_names(sc: JsonMapping) -> list[str]:
    names: dict[str, None] = {}

    def add(value: Any) -> None:
        name = text_value(value)
        if name:
            names.setdefault(name, None)

    for item in as_list(sc.get("competitors")):
        add(item)
    for name in feature_competitors(sc, as_list(as_mapping(sc.get("feature_tree")).get("rows"))):
        add(name)
    for tier in pricing_tiers(sc):
        add(tier.get("competitor"))
    for persona in personas(sc):
        add(persona.get("competitor"))
    for block in swot_blocks(sc):
        add(block.get("competitor"))
    for gap in as_list(sc.get("data_gaps")):
        add(as_mapping(gap).get("competitor"))
    return list(names)


def _failed_competitor_names(sc: JsonMapping) -> set[str]:
    # data_gaps marks competitors whose collection produced no usable source — the
    # signal that separates "draft" (nothing usable) from "partial" (some competitor
    # delivered real data, only specific fields need review).
    return {
        name
        for gap in as_list(sc.get("data_gaps"))
        if (name := text_value(as_mapping(gap).get("competitor")))
    }


def _quality_status(report: Report) -> str:
    if report.qa_status != "issues":
        return ""
    sc = report_structured_content(report)
    competitors = _report_competitor_names(sc)
    failed = _failed_competitor_names(sc)
    usable = [name for name in competitors if name not in failed]

    # Partial: at least one competitor cleared collection. Grade the run by data
    # completeness instead of flatly failing the whole report on any single gap.
    if usable:
        if failed:
            failed_label = "、".join(name for name in competitors if name in failed)
            detail = (
                f"{html_text('、'.join(usable))} 已采集到有效数据；"
                f"{html_text(failed_label)} 网络采集失败、本报告暂无其有效数据。"
                "部分字段仍需复核，详见下方缺口说明。"
            )
        else:
            detail = (
                "竞品数据已采集，部分字段缺少可验证来源、暂列为待复核，"
                "详见下方字段缺口说明。"
            )
        return f"""
<section class="quality-warning partial" role="status" aria-label="质量门部分通过">
  <strong>部分可用</strong>
  <span>{detail}</span>
</section>
"""

    # Draft: collection broadly failed or no competitor could be graded.
    return """
<section class="quality-warning" role="alert" aria-label="质量门未通过">
  <strong>草稿 / 待复核</strong>
  <span>本报告未通过质量门，不可作为正式交付。请先处理阻塞问题并复核关键结论。</span>
</section>
"""


def _data_gaps_banner(sc: JsonMapping) -> str:
    gaps = [as_mapping(gap) for gap in as_list(sc.get("data_gaps"))]
    gaps = [gap for gap in gaps if text_value(gap.get("competitor"))]
    if not gaps:
        return ""
    items = "\n".join(
        f"<li><b>{html_text(gap.get('competitor'))}</b>：数据采集失败，"
        f"本报告不含其有效数据（{html_text(gap.get('reason') or '原因未知')}）</li>"
        for gap in gaps
    )
    return f"""
<section class="data-gaps" role="alert" aria-label="数据缺失警示">
  <p>⚠️ 以下竞品的网络采集未获得可用来源，对应章节为空或不完整：</p>
  <ul>{items}</ul>
</section>
"""


def _field_gaps_banner(sc: JsonMapping) -> str:
    gaps = [as_mapping(gap) for gap in as_list(sc.get("field_gaps"))]
    gaps = [gap for gap in gaps if text_value(gap.get("message"))]
    if not gaps:
        return ""
    items = "\n".join(
        f"<li><b>{html_text(gap.get('competitor'))}</b> · "
        f"{html_text(gap.get('message'))}</li>"
        for gap in gaps
    )
    return f"""
<section class="field-gaps" role="note" aria-label="字段缺口说明">
  <p>以下字段缺少可验证证据，已保留为待复核缺口：</p>
  <ul>{items}</ul>
</section>
"""


def _feature_matrix(sc: JsonMapping, cite: CitationIndex) -> str:
    feature_tree = as_mapping(sc.get("feature_tree"))
    rows = as_list(feature_tree.get("rows"))
    if not rows:
        return ""
    competitors = feature_competitors(sc, rows)
    headers = ["功能", *competitors]
    body_rows: list[str] = []
    for row_value in rows:
        row = as_mapping(row_value)
        feature = text_value(row.get("feature"))
        description = text_value(row.get("description"))
        cells_by_competitor = {
            text_value(as_mapping(cell).get("competitor")): as_mapping(cell)
            for cell in as_list(row.get("cells"))
        }
        cells = [
            f"<td><strong>{html_text(feature)}</strong>{cite.html_marker(row.get('source_ids'))}"
            f"{f'<small>{html_text(description)}</small>' if description else ''}</td>"
        ]
        for competitor in competitors:
            cells.append(f"<td>{_support_cell(cells_by_competitor.get(competitor, {}))}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    intro = text_value(feature_tree.get("intro"))
    body = _intro_paragraph(intro, drop_cap=True) + _table(headers, body_rows)
    return _chapter(1, "功能树", body)


def _pricing_table(sc: JsonMapping, cite: CitationIndex) -> str:
    pricing = as_mapping(sc.get("pricing"))
    tiers = pricing_tiers(sc)
    if not tiers:
        return _chapter(
            2,
            "定价模型",
            (
                '<p class="gap-note">定价模型：未找到可验证定价来源。'
                "请补充官网、广告报价、商业化或创作者激励等来源后重新生成。</p>"
            ),
        )
    rows = [
        "<tr>"
        f"<td>{html_text(tier.get('competitor'))}</td>"
        f"<td>{html_text(tier.get('tier'))}</td>"
        f"<td class=\"price\">{html_text(tier.get('price'))}</td>"
        f"<td>{html_text(list_text(tier.get('highlights')))}{cite.html_marker(tier.get('source_ids'))}</td>"
        "</tr>"
        for tier in tiers
    ]
    body = _intro_paragraph(text_value(pricing.get("intro"))) + _table(
        ["竞品", "档位", "价格", "亮点"], rows
    )
    return _chapter(2, "定价模型", body)


def _persona_cards(sc: JsonMapping, cite: CitationIndex) -> str:
    persona_section = as_mapping(sc.get("user_personas"))
    items = personas(sc)
    if not items:
        return ""
    cards = []
    for persona in items:
        needs = _bullet_list(as_list(persona.get("needs")))
        pains = _bullet_list(as_list(persona.get("pain_points")))
        evidence = text_value(persona.get("evidence"))
        quote = f"<blockquote>{html_text(evidence)}</blockquote>" if evidence else ""
        cards.append(
            "<article class=\"card\">"
            f"<p class=\"kicker\">{html_text(persona.get('competitor'))} · "
            f"{html_text(persona.get('size'))}</p>"
            f"<h3>{html_text(persona.get('label'))}</h3>"
            f"<p class=\"mini-heading\">需求</p>{needs}"
            f"<p class=\"mini-heading\">痛点</p>{pains}"
            f"{quote}"
            f"{cite.html_marker(persona.get('source_ids'))}"
            "</article>"
        )
    body = _intro_paragraph(text_value(persona_section.get("intro"))) + (
        f'<div class="card-grid">{"".join(cards)}</div>'
    )
    return _chapter(3, "用户画像", body)


def _swot_blocks(sc: JsonMapping, cite: CitationIndex) -> str:
    swot = as_mapping(sc.get("swot"))
    blocks = swot_blocks(sc)
    if not blocks:
        return ""
    rendered = []
    labels = (
        ("strengths", "Strengths"),
        ("weaknesses", "Weaknesses"),
        ("opportunities", "Opportunities"),
        ("threats", "Threats"),
    )
    for block in blocks:
        quadrants = []
        for key, label in labels:
            items = "".join(
                f"<li>{html_text(item)}{cite.html_marker(source_ids)}</li>"
                for item, source_ids in swot_item_entries(block, key)
            )
            if items:
                quadrants.append(f"<div><h4>{label}</h4><ul>{items}</ul></div>")
        if quadrants:
            rendered.append(
                "<article class=\"swot\">"
                f"<h3>{html_text(block.get('competitor'))}</h3>"
                f"<div class=\"swot-grid\">{''.join(quadrants)}</div>"
                "</article>"
            )
    gap_items = [
        gap
        for gap in as_list(sc.get("field_gaps"))
        if text_value(as_mapping(gap).get("field_path")) == "swot"
    ]
    gap_note = ""
    if gap_items:
        gap_note = (
            '<p class="gap-note">部分竞品 SWOT 缺少足够证据，已在字段缺口说明中标记。</p>'
        )
    if not rendered and not gap_note:
        return ""
    body = _intro_paragraph(text_value(swot.get("intro"))) + gap_note + "".join(rendered)
    return _chapter(4, "SWOT", body)


def _extensions(sc: JsonMapping, cite: CitationIndex) -> str:
    sections = []
    for offset, ext in enumerate(extension_sections(sc), start=5):
        bullets = []
        for bullet_value in as_list(ext.get("bullets")):
            bullet = as_mapping(bullet_value)
            points = "".join(
                f"<li>{html_text(point)}</li>"
                for point in (text_value(point) for point in as_list(bullet.get("points")))
                if point
            )
            if points:
                bullets.append(
                    '<article class="card">'
                    f"<h3>{html_text(bullet.get('competitor'))}</h3>"
                    f"<ul>{points}</ul>{cite.html_marker(bullet.get('source_ids'))}</article>"
                )
        title = text_value(ext.get("title")) or text_value(ext.get("dimension_id"))
        summary = text_value(ext.get("summary"))
        body = f"<h2>{html_text(title)}</h2>"
        if text_value(ext.get("intent")):
            body += f"<p class=\"intent\">意图：{html_text(ext.get('intent'))}</p>"
        if summary:
            body += f"<p class=\"intro\">{html_text(summary)}</p>"
        if bullets:
            body += f'<div class="card-grid">{"".join(bullets)}</div>'
        sections.append(
            _chapter(offset, title, body, kicker="AI 建议扩展维度", title_already_rendered=True)
        )
    return "\n".join(sections)


def _cross_analysis(sc: JsonMapping, *, index: int) -> str:
    cross = as_mapping(sc.get("cross_analysis"))
    summary = text_value(cross.get("differentiation_summary"))
    positioning = as_mapping(cross.get("positioning_map"))
    matrix = as_mapping(cross.get("feature_matrix"))
    parts = []
    if summary:
        parts.append(f"<p class=\"intro\">{html_text(summary)}</p>")
    matrix_rows = as_list(matrix.get("rows"))
    if matrix_rows:
        parts.append(_feature_matrix_table(sc, matrix_rows, as_list(matrix.get("competitors"))))
    positioning_card = _positioning_card(positioning)
    if positioning_card:
        parts.append(positioning_card)
    if not parts:
        return ""
    return _chapter(index, "跨竞品总结", "".join(parts))


def _survey_insights(sc: JsonMapping, *, index: int) -> str:
    items = []
    for survey in survey_results(sc):
        competitor = text_value(survey.get("competitor_name"))
        for insight_value in as_list(survey.get("insights")):
            insight = as_mapping(insight_value)
            point = text_value(insight.get("point"))
            if point:
                prefix = f"{competitor}: " if competitor else ""
                items.append(f"<li>{html_text(prefix + point)}</li>")
    if not items:
        return ""
    body = f'<ul class="insight-list">{"".join(items)}</ul>'
    return _chapter(index, "调研洞察", body)


def _claims(report: Report, *, index: int) -> str:
    sc = report_structured_content(report)
    findings = _summary_findings(sc)
    if not findings:
        return ""
    items = [f"<li>{html_text(item)}</li>" for item in findings]
    return _chapter(index, "关键结论", f'<ul class="insight-list">{"".join(items)}</ul>')


def _summary_findings(sc: JsonMapping) -> list[str]:
    findings: list[str] = []
    summary = text_value(sc.get("summary"))
    if summary:
        findings.append(summary)
    cross_summary = text_value(as_mapping(sc.get("cross_analysis")).get("differentiation_summary"))
    if cross_summary and cross_summary not in findings:
        findings.append(cross_summary)
    for gap in as_list(sc.get("field_gaps")):
        message = text_value(as_mapping(gap).get("message"))
        competitor = text_value(as_mapping(gap).get("competitor"))
        if message:
            findings.append(f"{competitor}：{message}" if competitor else message)
        if len(findings) >= 6:
            break
    return findings[:6]


def _sources(cite: CitationIndex, *, index: int) -> str:
    groups = []
    for title, sources in cite.ordered_groups():
        items = []
        for number, source in sources:
            source_title = text_value(source.title) or text_value(source.url) or source.id
            url = text_value(source.url)
            link = (
                f'<a href="{html_text(url)}">{html_text(source_title)}</a>'
                if url
                else html_text(source_title)
            )
            type_abbrev = _TYPE_ABBREV.get(source.type, source.type[:2])
            items.append(
                f'<li id="{html_text(source.id)}">'
                f"<strong>S{number}</strong> "
                f'<span class="source-type">{html_text(type_abbrev)}</span> '
                f"{link}<small>{html_text(source.id)}</small>"
                "</li>"
            )
        groups.append(
            f'<div class="source-group"><h3>{html_text(title)}</h3>'
            f'<ol>{"".join(items)}</ol></div>'
        )
    if not groups:
        return ""
    return _chapter(index, "来源", "".join(groups), class_name="sources")


def _table_section(title: str, headers: Iterable[str], rows: list[str]) -> str:
    if not rows:
        return ""
    header = "".join(f"<th>{html_text(item)}</th>" for item in headers)
    return f"""
<section class="chapter">
  <h2>{html_text(title)}</h2>
  <table>
    <thead><tr>{header}</tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""


def _chapter(
    index: int,
    title: str,
    body: str,
    *,
    kicker: str | None = None,
    class_name: str = "",
    title_already_rendered: bool = False,
) -> str:
    if not body:
        return ""
    chapter_class = f"chapter {class_name}".strip()
    heading = "" if title_already_rendered else f"<h2>{html_text(title)}</h2>"
    suffix = f" · {html_text(kicker)}" if kicker else ""
    return f"""
<section class="{chapter_class}">
  <div class="chapter-heading">
    <p class="eyebrow">Ch. {index:02d}{suffix}</p>
    {heading}
  </div>
  {body}
</section>
"""


def _intro_paragraph(value: str, *, drop_cap: bool = False) -> str:
    if not value:
        return ""
    class_name = "intro drop-cap" if drop_cap else "intro"
    return f'<p class="{class_name}">{html_text(value)}</p>'


def _table(headers: Iterable[str], rows: list[str]) -> str:
    header = "".join(f"<th>{html_text(item)}</th>" for item in headers)
    return (
        '<div class="table-wrap"><table>'
        f"<thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody>"
        "</table></div>"
    )


def _feature_matrix_table(
    sc: JsonMapping, rows: list[Any], competitor_values: list[Any] | None = None
) -> str:
    competitors = [
        text_value(item)
        for item in (competitor_values if competitor_values is not None else [])
        if text_value(item)
    ] or feature_competitors(sc, rows)
    body_rows: list[str] = []
    for row_value in rows:
        row = as_mapping(row_value)
        description = text_value(row.get("description"))
        description_html = f"<small>{html_text(description)}</small>" if description else ""
        cells_by_competitor = {
            text_value(as_mapping(cell).get("competitor")): as_mapping(cell)
            for cell in as_list(row.get("cells"))
        }
        cells = [f"<td><strong>{html_text(row.get('feature'))}</strong>{description_html}</td>"]
        for competitor in competitors:
            cells.append(f"<td>{_support_cell(cells_by_competitor.get(competitor, {}))}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return _table(["功能", *competitors], body_rows)


def _support_cell(cell: JsonMapping) -> str:
    status = text_value(cell.get("status")) or "unknown"
    note = text_value(cell.get("note")) or "—"
    tone = status if status in {"supported", "partial", "unsupported", "unknown"} else "unknown"
    glyph = {
        "supported": "●",
        "partial": "◐",
        "unsupported": "○",
        "unknown": "?",
    }[tone]
    return (
        f'<span class="support {tone}"><span aria-hidden="true">{glyph}</span>'
        f"<span>{html_text(note)}</span></span>"
    )


def _positioning_card(positioning: JsonMapping) -> str:
    points = []
    for idx, point_value in enumerate(as_list(positioning.get("competitors"))):
        point = as_mapping(point_value)
        x = finite_number(point.get("x"))
        y = finite_number(point.get("y"))
        label = text_value(point.get("label")) or text_value(point.get("id")) or f"Point {idx + 1}"
        if x is None or y is None:
            continue
        points.append(
            f'<span class="map-point" style="left:{max(0, min(100, x)):.2f}%;'
            f'top:{100 - max(0, min(100, y)):.2f}%;">'
            f"<b>{html_text(label)}</b></span>"
        )
    if not points:
        return ""
    return (
        '<article class="positioning">'
        f'<p class="mini-heading">定位图 · x: {html_text(positioning.get("x_axis"))} · '
        f'y: {html_text(positioning.get("y_axis"))}</p>'
        f'<div class="map">{"".join(points)}</div>'
        "</article>"
    )


def _pill_list(values: list[Any]) -> str:
    items = [text for text in (text_value(value) for value in values) if text]
    if not items:
        return '<span class="muted">暂无</span>'
    return (
        '<span class="pills">'
        + "".join(f"<span>{html_text(item)}</span>" for item in items)
        + "</span>"
    )


def _bullet_list(values: list[Any]) -> str:
    items = [text for text in (text_value(value) for value in values) if text]
    if not items:
        return '<p class="muted">暂无</p>'
    return "<ul>" + "".join(f"<li>{html_text(item)}</li>" for item in items) + "</ul>"


def _percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.0f}%"


_STYLE = """
@page { size: A4; margin: 18mm 16mm; background: #ffffff; }
* { box-sizing: border-box; }
html {
  background: #ffffff;
}
body {
  margin: 0;
  color: #111111;
  background: #ffffff;
  font-family:
    "Noto Sans CJK SC", "Microsoft YaHei", "PingFang SC",
    "Helvetica Neue", Arial, sans-serif;
  font-size: 11px;
  line-height: 1.58;
}
.report { max-width: 780px; margin: 0 auto; }
.masthead { border-bottom: 1px solid #d0d0d0; padding-bottom: 22px; margin-bottom: 18px; }
.eyebrow, .kicker {
  color: #666666;
  font-family: "Cascadia Mono", "SFMono-Regular", Consolas, monospace;
  font-size: 9px;
  letter-spacing: .14em;
  text-transform: uppercase;
}
h1, h2, h3, h4 {
  color: #111111;
  font-family: "Noto Serif SC", "Songti SC", "SimSun", serif;
  font-weight: 600;
  margin: 0;
}
h1 { font-size: 34px; line-height: 1.08; margin-top: 8px; }
h2 { font-size: 20px; margin-bottom: 12px; }
h3 { font-size: 14px; margin-bottom: 7px; }
h4 { font-size: 12px; margin-bottom: 6px; }
.subtitle {
  color: #555555;
  font-family: "Noto Serif SC", "Songti SC", serif;
  font-style: italic;
  font-size: 13px;
}
.summary { max-width: 68ch; font-size: 12px; }
.metrics { display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0 24px; }
.quality-warning {
  display: flex;
  gap: 10px;
  align-items: baseline;
  border: 1px solid #c93a32;
  border-left: 4px solid #c93a32;
  border-radius: 4px;
  background: #fff3f0;
  color: #5d1713;
  padding: 10px 14px;
  margin: 0 0 16px;
  font-size: 12px;
}
.quality-warning strong { white-space: nowrap; }
.quality-warning.partial {
  border-color: #e0b400;
  border-left-color: #e0b400;
  background: #fffaeb;
  color: #5a4500;
}
.data-gaps {
  border: 1px solid #e0b400;
  border-left: 4px solid #e0b400;
  border-radius: 4px;
  background: #fffaeb;
  padding: 10px 14px;
  margin: 0 0 24px;
  font-size: 12px;
}
.data-gaps p { margin: 0 0 6px; font-weight: 600; }
.data-gaps ul { margin: 0; padding-left: 18px; }
.field-gaps {
  border: 1px solid #d9d9d9;
  border-left: 4px solid #666666;
  border-radius: 4px;
  background: #f8f8f8;
  padding: 10px 14px;
  margin: 0 0 24px;
  font-size: 12px;
}
.field-gaps p { margin: 0 0 6px; font-weight: 600; }
.field-gaps ul { margin: 0; padding-left: 18px; }
.gap-note {
  border: 1px dashed #bdbdbd;
  border-radius: 4px;
  background: #fbfbfb;
  color: #555555;
  padding: 10px 12px;
}
.metric {
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 7px 9px;
  min-width: 90px;
  background: #ffffff;
  color: #555555;
}
.metric b { display: block; color: #111111; font-size: 15px; }
.chapter { break-inside: avoid; margin: 0 0 24px; }
table { width: 100%; border-collapse: collapse; background: #ffffff; }
th, td {
  border-bottom: 1px solid #dedede;
  padding: 8px 7px;
  text-align: left;
  vertical-align: top;
}
th {
  color: #555555;
  font-family: "Cascadia Mono", "SFMono-Regular", Consolas, monospace;
  font-size: 9px;
  letter-spacing: .08em;
  text-transform: uppercase;
}
td small, .sources small { display: block; color: #666666; margin-top: 3px; }
.cites { white-space: nowrap; margin-left: 4px; font-size: 9px; vertical-align: super; }
.cite {
  border: 1px solid #d9d9d9;
  border-radius: 3px;
  color: #555555;
  font-family: "Cascadia Mono", "SFMono-Regular", Consolas, monospace;
  margin-left: 2px;
  padding: 0 3px;
  text-decoration: none;
}
.source-group { margin-bottom: 14px; }
.source-group h3 {
  color: #666666;
  font-family: "Cascadia Mono", "SFMono-Regular", Consolas, monospace;
  font-size: 9px;
  letter-spacing: .14em;
  text-transform: uppercase;
}
.source-type {
  color: #666666;
  font-family: "Cascadia Mono", "SFMono-Regular", Consolas, monospace;
}
.card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.card, .swot {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 10px;
  background: #ffffff;
  break-inside: avoid;
}
.evidence { color: #555555; font-style: italic; }
.muted { color: #666666; }
.pills { display: flex; flex-wrap: wrap; gap: 4px; margin-left: 6px; }
.pills span {
  display: inline-block;
  border: 1px solid #d9d9d9;
  border-radius: 3px;
  padding: 1px 4px;
  color: #333333;
  background: #ffffff;
}
.swot { margin-bottom: 10px; }
.swot-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px 14px; }
ul, ol { margin: 7px 0 0; padding-left: 18px; }
li { margin: 3px 0; }
.sources li { margin-bottom: 8px; }
"""
