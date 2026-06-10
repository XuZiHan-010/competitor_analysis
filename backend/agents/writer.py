from collections.abc import Mapping
from uuid import UUID

import structlog

from graph.state import WorkflowState
from schemas.report import Report, ReportClaim
from services.agents.decorators import traced_node
from services.llm import LLMClient
from services.llm.usage import record_degradation
from services.metrics import calculate_report_metrics
from services.report_integrity import (
    assert_report_sources_resolvable,
    placeholder_issues,
)
from settings import get_settings

logger = structlog.get_logger(__name__)

_FEATURE_STATUS_ALIASES = {
    "supported": "supported",
    "support": "supported",
    "yes": "supported",
    "true": "supported",
    "available": "supported",
    "支持": "supported",
    "partial": "partial",
    "partially_supported": "partial",
    "limited": "partial",
    "weak": "partial",
    "部分支持": "partial",
    "有限支持": "partial",
    "unsupported": "unsupported",
    "not_supported": "unsupported",
    "no": "unsupported",
    "false": "unsupported",
    "unavailable": "unsupported",
    "不支持": "unsupported",
    "unknown": "unknown",
    "unverified": "unknown",
    "unchecked": "unknown",
    "": "unknown",
}


def _canonical_feature_status(value: object) -> str:
    return _FEATURE_STATUS_ALIASES.get(str(value or "").strip().lower(), "unknown")


def _canonical_feature_cell(cell: Mapping[str, object], competitor: str) -> dict[str, object]:
    return {
        **dict(cell),
        "competitor": str(cell.get("competitor") or competitor),
        "status": _canonical_feature_status(cell.get("status")),
        "note": str(cell.get("note") or ""),
    }


class WriterAgent:
    @traced_node(
        agent_name="WriterAgent",
        node_name="run_writer",
        prompt="Render a structured report with citations and multilingual-ready claims.",
    )
    async def run(
        self,
        state: WorkflowState,
        *,
        trace_context: object | None = None,
        language: str = "zh",
    ) -> Report:
        settings = get_settings()
        llm = LLMClient(settings, max_output_tokens=16384)
        if settings.mock_llm:
            return self._run_fallback(state, language=language)
        if not settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for WriterAgent in real mode")
        try:
            return await self._run_llm(state, llm, language=language)
        except Exception as exc:
            logger.warning("writer_llm_failed", exc_info=True)
            record_degradation(f"writer: {type(exc).__name__}: {exc}")
            raise RuntimeError(f"WriterAgent LLM failed: {type(exc).__name__}: {exc}") from exc

    async def _run_llm(self, state: WorkflowState, llm: LLMClient, *, language: str) -> Report:
        settings = get_settings()
        sources = [s for result in state.raw_collections.values() for s in result.sources]
        source_ids_by_profile = {
            name: profile.source_ids for name, profile in state.structured_profiles.items()
        }
        profiles_payload = [p.model_dump(mode="json") for p in state.structured_profiles.values()]
        dims_payload = [d.model_dump() for d in state.scope_contract.dimensions if d.enabled]
        simulated_warnings = _build_simulated_warnings(state)

        payload = await llm.complete_json(
            provider="deepseek",
            model=settings.writer_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are WriterAgent. Return a valid JSON object with markdown, "
                        "section_intros, summary, and claims. markdown must be a complete "
                        "long-form competitive analysis report with heading hierarchy, "
                        "cross-competitor comparison paragraphs, and a conclusion in the "
                        "requested language. section_intros must be an object keyed by "
                        "feature_tree, pricing, user_personas, swot, cross_analysis, and "
                        "each enabled extension dimension id; each value must be a narrative "
                        "intro with cross-competitor insight, not a table recap. Synthesize "
                        "differences, name strengths and weaknesses, and omit unsupported "
                        "points. Every claim must include source_ids copied from the provided "
                        "profiles. Do not output placeholder text such as 待确认, 需验证, "
                        "标准版, unknown, TBD, or needs verification. For any survey insight "
                        "backed only by AI-simulated evidence, prefix the text with "
                        "'⚠️ [AI模拟] '."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Language: {language}\n"
                        f"Dimensions (ordered): {dims_payload}\n"
                        f"Profiles: {profiles_payload}\n"
                        f"Allowed source ids: {source_ids_by_profile}\n"
                        f"AI-simulated survey sections requiring ⚠️: {simulated_warnings}"
                    ),
                },
            ],
        )
        section_intros = _section_intros_from_payload(payload.get("section_intros"))
        rich = self._assemble_rich_content(state, language, section_intros=section_intros)
        rich["summary"] = payload.get("summary", "") or rich["summary"]
        structured_content = rich
        # Claims are derived field-by-field from the assembled structured content
        # (its per-field source_ids are authoritative) plus deterministic survey
        # claims — not from the LLM's free-text claim list, so every visible
        # cell/tier/persona/bullet maps to a traceable claim.
        claims = _field_level_core_claims(state, structured_content) + _survey_claims(
            state, sources
        )
        markdown = str(payload.get("markdown") or "").strip() or self._render_markdown(
            structured_content
        )
        return self._build_report(state, structured_content, markdown, claims, sources, language)

    def _run_fallback(self, state: WorkflowState, *, language: str) -> Report:
        sources = [s for result in state.raw_collections.values() for s in result.sources]
        structured_content = self._assemble_rich_content(state, language)
        claims = _field_level_core_claims(state, structured_content) + _survey_claims(
            state, sources
        )
        markdown = self._render_markdown(structured_content)
        return self._build_report(state, structured_content, markdown, claims, sources, language)

    def _assemble_rich_content(
        self,
        state: WorkflowState,
        language: str,
        *,
        section_intros: Mapping[str, str] | None = None,
    ) -> dict:
        """Pivot per-competitor AnalystAgent output into canonical cross-competitor structure."""
        profiles = state.structured_profiles
        competitors = list(profiles.keys())

        # feature_tree: pivot per-competitor rows into cross-competitor matrix
        feature_index: dict[str, dict] = {}
        for name, profile in profiles.items():
            for row in profile.feature_tree.get("rows") or []:
                feat = str(row.get("feature", ""))
                if not feat:
                    continue
                if feat not in feature_index:
                    feature_index[feat] = {
                        "feature": feat,
                        "description": row.get("description", ""),
                        "cells": [],
                        "source_ids": [],
                    }
                cell = next(
                    (
                        c
                        for c in (row.get("cells") or [])
                        if isinstance(c, Mapping) and c.get("competitor") == name
                    ),
                    {"competitor": name, "status": "unknown", "note": ""},
                )
                feature_index[feat]["cells"].append(_canonical_feature_cell(cell, name))
                feature_index[feat]["source_ids"].extend(row.get("source_ids") or [])
        ft_rows = list(feature_index.values())
        for row in ft_rows:
            row["source_ids"] = list(dict.fromkeys(row["source_ids"]))

        # pricing: merge all tier lists
        all_tiers: list[dict] = []
        for profile in profiles.values():
            all_tiers.extend(profile.pricing.get("tiers") or [])

        # user_personas: merge all persona lists
        all_personas: list[dict] = []
        for profile in profiles.values():
            personas = profile.user_personas if isinstance(profile.user_personas, list) else []
            all_personas.extend(personas)

        # swot: one block per competitor
        swot_blocks: list[dict] = []
        for name, profile in profiles.items():
            swot = profile.swot
            swot_blocks.append({
                "competitor": name,
                "strengths": swot.get("strengths") or [],
                "weaknesses": swot.get("weaknesses") or [],
                "opportunities": swot.get("opportunities") or [],
                "threats": swot.get("threats") or [],
            })

        # extensions: group extension_findings by dimension_id
        ext_by_dim: dict[str, dict] = {}
        for finding in state.extension_findings:
            did = finding.dimension_id
            dim = next(
                (d for d in state.scope_contract.dimensions if d.id == did),
                None,
            )
            if did not in ext_by_dim:
                ext_by_dim[did] = {
                    "dimension_id": did,
                    "title": dim.title if dim else did,
                    "intent": dim.intent if dim else "",
                    "summary": finding.summary,
                    "bullets": [],
                }
            ext_by_dim[did]["bullets"].append({
                "competitor": finding.competitor_name,
                "points": finding.bullets,
                "source_ids": finding.source_ids,
            })
        extensions = list(ext_by_dim.values())

        # cross_analysis
        cross: dict = {}
        if state.cross_analysis:
            cross = state.cross_analysis.model_dump(mode="json")

        intros = section_intros or {}
        title = f"{', '.join(competitors)} 竞品分析报告" if competitors else "竞品分析报告"
        content = {
            "title": title,
            "subtitle": f"基于 {len(competitors)} 个竞品的深度分析",
            "summary": f"本报告分析了 {', '.join(competitors)} 的竞争格局。",
            "language": language,
            "competitors": competitors,
            "feature_tree": {"intro": intros.get("feature_tree", ""), "rows": ft_rows},
            "pricing": {"intro": intros.get("pricing", ""), "tiers": all_tiers},
            "user_personas": {"intro": intros.get("user_personas", ""), "personas": all_personas},
            "swot": {"intro": intros.get("swot", ""), "blocks": swot_blocks},
            "extensions": _apply_extension_intros(extensions, intros),
            "cross_analysis": _apply_section_intro(cross, intros.get("cross_analysis", "")),
            "survey": [r.model_dump(mode="json") for r in state.survey_results.values()],
            "field_verification_status": state.field_verification_status,
        }
        return content | _field_status_overrides(
            state,
            ft_rows,
            all_tiers,
            all_personas,
            swot_blocks,
            section_intros=intros,
        )

    def _render_markdown(self, structured_content: Mapping[str, object]) -> str:
        title = str(structured_content.get("title") or "Competitor Analysis Report")
        lines = [f"# {title}", ""]
        summary = str(structured_content.get("summary") or "").strip()
        if summary:
            lines.extend(["## Executive Summary", summary, ""])

        feature_tree = _mapping(structured_content.get("feature_tree"))
        feature_rows = _list_of_mappings(feature_tree.get("rows"))
        lines.extend(_markdown_section("Feature Comparison", feature_tree.get("intro")))
        if feature_rows:
            lines.extend(["| Feature | Competitor Signals | Sources |", "|---|---|---|"])
            for row in feature_rows:
                cells = _list_of_mappings(row.get("cells"))
                signals = "; ".join(
                    _compact_join(
                        [
                            str(cell.get("competitor") or ""),
                            str(cell.get("status") or ""),
                            str(cell.get("note") or ""),
                        ],
                        separator=": ",
                    )
                    for cell in cells
                )
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            _markdown_cell(row.get("feature")),
                            _markdown_cell(signals),
                            _markdown_cell(", ".join(_strings(row.get("source_ids")))),
                        ]
                    )
                    + " |"
                )
            lines.append("")

        pricing = _mapping(structured_content.get("pricing"))
        tiers = _list_of_mappings(pricing.get("tiers"))
        lines.extend(_markdown_section("Pricing", pricing.get("intro")))
        if tiers:
            lines.extend(
                ["| Competitor | Tier | Price | Highlights | Sources |", "|---|---|---|---|---|"]
            )
            for tier in tiers:
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            _markdown_cell(tier.get("competitor")),
                            _markdown_cell(tier.get("tier") or tier.get("plan_name")),
                            _markdown_cell(tier.get("price")),
                            _markdown_cell(", ".join(_strings(tier.get("highlights")))),
                            _markdown_cell(", ".join(_strings(tier.get("source_ids")))),
                        ]
                    )
                    + " |"
                )
            lines.append("")

        personas = _mapping(structured_content.get("user_personas"))
        persona_rows = _list_of_mappings(personas.get("personas"))
        lines.extend(_markdown_section("User Personas", personas.get("intro")))
        if persona_rows:
            lines.extend(
                ["| Competitor | Persona | Needs | Evidence | Sources |", "|---|---|---|---|---|"]
            )
            for persona in persona_rows:
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            _markdown_cell(persona.get("competitor")),
                            _markdown_cell(persona.get("label")),
                            _markdown_cell(", ".join(_strings(persona.get("needs")))),
                            _markdown_cell(persona.get("evidence")),
                            _markdown_cell(", ".join(_strings(persona.get("source_ids")))),
                        ]
                    )
                    + " |"
                )
            lines.append("")

        swot = _mapping(structured_content.get("swot"))
        lines.extend(_markdown_section("SWOT", swot.get("intro")))
        for block in _list_of_mappings(swot.get("blocks")):
            lines.extend([f"### {block.get('competitor')}", ""])
            for key, label in (
                ("strengths", "Strengths"),
                ("weaknesses", "Weaknesses"),
                ("opportunities", "Opportunities"),
                ("threats", "Threats"),
            ):
                items = _list_value(block.get(key))
                if items:
                    lines.append(f"**{label}:**")
                    lines.extend(f"- {_item_text(item)}" for item in items)
                    lines.append("")

        for extension in _list_of_mappings(structured_content.get("extensions")):
            lines.extend(
                _markdown_section(
                    str(extension.get("title") or "Extension"),
                    extension.get("intro"),
                )
            )
            for bullet in _list_of_mappings(extension.get("bullets")):
                competitor = bullet.get("competitor")
                points = "; ".join(_strings(bullet.get("points")))
                if points:
                    lines.append(f"- **{competitor}:** {points}")
            lines.append("")

        cross = _mapping(structured_content.get("cross_analysis"))
        lines.extend(_markdown_section("Cross Analysis", cross.get("intro")))
        cross_summary = cross.get("differentiation_summary")
        if cross_summary:
            lines.extend([str(cross_summary), ""])
        lines.extend(["## Conclusion", "以上结论均基于已采集来源与结构化字段生成。", ""])
        return "\n".join(lines).strip() + "\n"

    def _build_report(
        self,
        state: WorkflowState,
        structured_content: dict,
        markdown: str,
        claims: list[ReportClaim],
        sources: list,
        language: str,
    ) -> Report:
        integrity_issues = placeholder_issues(
            structured_content=structured_content,
            markdown_content=markdown,
        )
        assert_report_sources_resolvable(
            sources=sources,
            claims=claims,
            structured_content=structured_content,
        )
        metrics = calculate_report_metrics(
            claims=claims,
            sources=sources,
            structured_content=structured_content,
            field_verification_status=state.field_verification_status,
            rerun_count=sum(state.retry_counts.values()),
            module_count=max(len(state.scope_contract.dimensions), 1),
            ai_self_assessment={
                "confidence": "needs_review",
                "needs_human_review": bool(integrity_issues)
                or bool(state.field_verification_status)
                or bool(state.qa_result and not state.qa_result.passed),
                "integrity_issues": integrity_issues,
                "field_verification_status": state.field_verification_status,
            },
        )
        qa_issues = (
            [issue.model_dump(mode="json") for issue in state.qa_result.issues]
            if state.qa_result
            else []
        )
        qa_issues.extend(integrity_issues)
        qa_issues.extend(_field_status_issues(state.field_verification_status))
        return Report(
            task_id=UUID(str(state.task_id)),
            language="zh" if language not in {"zh", "en"} else language,
            structured_content=structured_content,
            markdown_content=markdown,
            sources=sources,
            claims=claims,
            metrics=metrics,
            qa_status=(
                "issues"
                if integrity_issues
                or state.field_verification_status
                or (state.qa_result and not state.qa_result.passed)
                else "passed"
            ),
            qa_issues=qa_issues,
        )


def _build_simulated_warnings(state: WorkflowState) -> list[dict]:
    """Return a list of survey competitors whose evidence is predominantly AI-simulated."""
    warnings = []
    for competitor, survey in state.survey_results.items():
        if not survey.evidence:
            continue
        simulated = sum(1 for e in survey.evidence if e.source_type == "ai_simulated")
        ratio = simulated / len(survey.evidence)
        if ratio > 0:
            warnings.append({
                "competitor": competitor,
                "ai_simulated_ratio": round(ratio, 2),
                "note": "⚠️ mark required on insights from simulated evidence",
            })
    return warnings


def _source_support_for_state(state: WorkflowState, source_ids: list[str]) -> str:
    if not source_ids:
        return "unchecked"
    if state.qa_result and state.qa_result.passed:
        return "supported"
    return "unchecked"


def _field_status_overrides(
    state: WorkflowState,
    feature_rows: list[dict],
    tiers: list[dict],
    personas: list[dict],
    swot_blocks: list[dict],
    *,
    section_intros: Mapping[str, str] | None = None,
) -> dict:
    if not state.field_verification_status:
        return {}

    intros = section_intros or {}
    notes: list[dict] = []
    for item in state.field_verification_status.values():
        if not isinstance(item, Mapping):
            continue
        competitor = str(item.get("competitor", ""))
        field_path = str(item.get("field_path", ""))
        reason = str(item.get("reason", "该字段未获充分证据支撑。"))
        status = str(item.get("status", "unverified"))
        notes.append({
            "competitor": competitor,
            "field_path": field_path,
            "status": status,
            "message": f"未确认：{reason}",
            "source_ids": item.get("source_ids", []),
        })
        if field_path == "feature_tree":
            _mark_feature_cells_unverified(feature_rows, competitor, reason)

    return {
        "feature_tree": {"intro": intros.get("feature_tree", ""), "rows": feature_rows},
        "pricing": {
            "intro": intros.get("pricing", ""),
            "tiers": tiers,
            "unverified_notes": notes,
        },
        "user_personas": {
            "intro": intros.get("user_personas", ""),
            "personas": personas,
            "unverified_notes": notes,
        },
        "swot": {"intro": intros.get("swot", ""), "blocks": swot_blocks, "unverified_notes": notes},
        "unverified_fields": notes,
    }


def _mark_feature_cells_unverified(
    feature_rows: list[dict],
    competitor: str,
    reason: str,
) -> None:
    for row in feature_rows:
        for cell in row.get("cells") or []:
            if (
                str(cell.get("competitor", "")).lower() == competitor.lower()
                and str(cell.get("status", "")).lower() == "unknown"
            ):
                cell["note"] = f"未确认：{reason}"


def _field_status_issues(field_status: dict[str, object]) -> list[dict]:
    issues: list[dict] = []
    for item in field_status.values():
        if not isinstance(item, Mapping):
            continue
        issues.append({
            "severity": "warning",
            "target_agent": "CollectorAgent",
            "target_competitor": item.get("competitor"),
            "failed_field": item.get("field_path"),
            "message": item.get("reason", "字段未获充分证据支撑。"),
            "retryable": False,
        })
    return issues


def _field_level_core_claims(
    state: WorkflowState,
    structured_content: Mapping[str, object],
) -> list[ReportClaim]:
    """One claim per visible core/extension field, citing that field's source_ids.

    Field-level (not profile-level) so every cell, tier, persona, SWOT item, and
    extension bullet in the report maps to a traceable claim; citation coverage
    then measures the report body, not a single rolled-up summary per competitor.
    """
    claims: list[ReportClaim] = []

    def _add(path: str, text: str, source_ids: list[str], layer: str) -> None:
        ids = list(dict.fromkeys(source_ids))
        claims.append(
            ReportClaim(
                claim_path=path,
                claim_text=text.strip() or path,
                layer=layer,
                field_type="structured",
                source_ids=ids,
                generating_agent="WriterAgent",
                source_support=_source_support_for_state(state, ids),
                validity="valid" if ids else "unknown",
            )
        )

    feature = _mapping(structured_content.get("feature_tree"))
    for i, row in enumerate(_list_of_mappings(feature.get("rows"))):
        _add(f"feature_tree.rows[{i}]", str(row.get("feature") or ""),
             _strings(row.get("source_ids")), "core")

    pricing = _mapping(structured_content.get("pricing"))
    for i, tier in enumerate(_list_of_mappings(pricing.get("tiers"))):
        label = _compact_join(
            [
                str(tier.get("competitor") or ""),
                str(tier.get("tier") or tier.get("plan_name") or ""),
                str(tier.get("price") or ""),
            ],
            separator=" · ",
        )
        _add(f"pricing.tiers[{i}]", label, _strings(tier.get("source_ids")), "core")

    personas = _mapping(structured_content.get("user_personas"))
    for i, persona in enumerate(_list_of_mappings(personas.get("personas"))):
        label = _compact_join(
            [str(persona.get("competitor") or ""), str(persona.get("label") or "")],
            separator=" · ",
        )
        _add(f"user_personas.personas[{i}]", label, _strings(persona.get("source_ids")), "core")

    swot = _mapping(structured_content.get("swot"))
    for b, block in enumerate(_list_of_mappings(swot.get("blocks"))):
        for quadrant in ("strengths", "weaknesses", "opportunities", "threats"):
            for i, item in enumerate(_list_of_mappings(block.get(quadrant))):
                _add(f"swot.blocks[{b}].{quadrant}[{i}]", str(item.get("text") or ""),
                     _strings(item.get("source_ids")), "core")

    for e, extension in enumerate(_list_of_mappings(structured_content.get("extensions"))):
        for i, bullet in enumerate(_list_of_mappings(extension.get("bullets"))):
            _add(f"extensions[{e}].bullets[{i}]", "; ".join(_strings(bullet.get("points"))),
                 _strings(bullet.get("source_ids")), "extension")

    return claims


def _survey_claims(state: WorkflowState, sources: list) -> list[ReportClaim]:
    """Deterministic survey-layer claims mapping insight evidence to report sources."""
    evidence_index = {
        e.id: e for survey in state.survey_results.values() for e in survey.evidence
    }
    report_source_ids = {source.id for source in sources}
    claims: list[ReportClaim] = []
    for index, (_, survey) in enumerate(state.survey_results.items(), start=1):
        for insight_index, insight in enumerate(survey.insights, start=1):
            source_support = "supported" if insight.confidence != "low" else "weak"
            all_simulated = bool(insight.evidence_ids) and all(
                evidence_index.get(eid) is not None
                and evidence_index[eid].source_type == "ai_simulated"
                for eid in insight.evidence_ids
            )
            claim_text = f"⚠️ [AI模拟] {insight.point}" if all_simulated else insight.point
            claims.append(
                ReportClaim(
                    claim_path=f"survey[{index}].insights[{insight_index}]",
                    claim_text=claim_text,
                    layer="survey",
                    field_type="free_text",
                    source_ids=_survey_insight_source_ids(
                        evidence_index, insight.evidence_ids, report_source_ids
                    ),
                    generating_agent="SurveyTool",
                    source_support=source_support,
                    validity="valid",
                )
            )
    return claims


def _survey_insight_source_ids(
    evidence_index: Mapping[str, object],
    evidence_ids: list[str],
    report_source_ids: set[str],
) -> list[str]:
    source_ids: list[str] = []
    for evidence_id in evidence_ids:
        evidence = evidence_index.get(evidence_id)
        source_id = getattr(evidence, "source_id", None)
        if isinstance(source_id, str) and source_id in report_source_ids:
            source_ids.append(source_id)
    return list(dict.fromkeys(source_ids))


def _section_intros_from_payload(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): str(intro).strip()
        for key, intro in value.items()
        if isinstance(key, str) and isinstance(intro, str) and intro.strip()
    }


def _apply_extension_intros(
    extensions: list[dict],
    section_intros: Mapping[str, str],
) -> list[dict]:
    return [
        {
            **extension,
            "intro": section_intros.get(str(extension.get("dimension_id") or ""), ""),
        }
        for extension in extensions
    ]


def _apply_section_intro(value: dict, intro: str) -> dict:
    if not value and not intro:
        return value
    return {**value, "intro": intro}


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: object) -> list[Mapping[str, object]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _list_value(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _markdown_section(title: str, intro: object) -> list[str]:
    lines = [f"## {title}", ""]
    text = str(intro or "").strip()
    if text:
        lines.extend([text, ""])
    return lines


def _markdown_cell(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def _compact_join(values: list[str], *, separator: str) -> str:
    meaningful = [value for value in values if value]
    if not meaningful:
        return ""
    return separator.join(meaningful[:2]) + (
        f" ({meaningful[2]})" if len(meaningful) > 2 else ""
    )


def _item_text(item: object) -> str:
    if isinstance(item, Mapping):
        text = str(item.get("text") or item.get("summary") or "")
        source_ids = item.get("source_ids") or []
        suffix = f" [{', '.join(map(str, source_ids))}]" if source_ids else ""
        return f"{text}{suffix}".strip()
    return str(item)
