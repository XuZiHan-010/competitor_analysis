from datetime import UTC, datetime

import structlog

from graph.state import (
    QAIssue,
    QAResult,
    RawCollectionResult,
    StructuredCompetitorProfile,
    WorkflowState,
)
from schemas.source import SourceCitation
from services.agents.decorators import traced_node
from services.llm import LLMClient
from settings import get_settings

_MIN_SOURCES_PER_COMPETITOR = 5
_SOURCE_STALENESS_YEARS = 2
_MAX_FEATURE_UNKNOWN_RATE = 0.4
_MIN_SWOT_NON_EMPTY_QUADRANTS = 2
_MAX_FACT_CHECK_SAMPLES = 8

logger = structlog.get_logger(__name__)


class QAAgent:
    @traced_node(
        agent_name="QAAgent",
        node_name="check_qa",
        prompt="Validate schema completeness, source support, and feedback loop blockers.",
    )
    async def run(
        self,
        state: WorkflowState,
        *,
        trace_context: object | None = None,
    ) -> QAResult:
        settings = get_settings()
        llm = LLMClient(settings)
        if llm.enabled and settings.openai_api_key:
            try:
                return await self._run_llm(state, llm)
            except Exception:
                logger.warning("qa_llm_failed_falling_back", exc_info=True)
        return self._run_fallback(state)

    async def _run_llm(self, state: WorkflowState, llm: LLMClient) -> QAResult:
        settings = get_settings()
        profiles_payload = [p.model_dump(mode="json") for p in state.structured_profiles.values()]
        sources_payload = [
            s.model_dump(mode="json")
            for result in state.raw_collections.values()
            for s in result.sources
        ]
        fact_check_payload = _fact_check_samples(state)
        payload = await llm.complete_json(
            provider="openai",
            model=settings.qa_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are QAAgent. Return JSON: {passed:boolean, issues:[{severity,"
                        "target_agent,target_competitor,failed_field,message,retryable,code}]}. "
                        "code must be stable snake_case, such as pricing_missing, "
                        "pricing_source_weak, swot_incomplete, source_count_low, "
                        "feature_tree_sparse, or citation_missing. "
                        "Treat unsupported or contradictory sampled claims as blocker issues "
                        "targeting CollectorAgent."
                    ),
                },
                {
                    "role": "user",
                    "content": (f"Profiles: {profiles_payload}\n" f"Sources: {sources_payload}"),
                },
                {
                    "role": "user",
                    "content": f"Fact-check samples: {fact_check_payload}",
                },
            ],
        )
        issues = [
            QAIssue(
                severity=str(issue.get("severity", "warning")),
                target_agent=str(issue.get("target_agent", "AnalystAgent")),
                target_competitor=issue.get("target_competitor"),
                failed_field=str(issue.get("failed_field", "unknown")),
                message=str(issue.get("message", "")),
                retryable=_parse_llm_retryable(issue),
                code=str(
                    issue.get("code")
                    or _issue_code(str(issue.get("failed_field", "unknown")))
                ),
            )
            for issue in payload.get("issues", [])
        ]
        # Always also run deterministic checks alongside LLM checks
        deterministic = self._deterministic_checks(state)
        all_issues = _apply_unrecoverable_override(issues + deterministic.issues, state)
        all_issues = _apply_analyst_failure_override(all_issues, state)
        return QAResult(
            passed=not any(i.severity == "blocker" for i in all_issues),
            issues=all_issues,
        )

    def _run_fallback(self, state: WorkflowState) -> QAResult:
        issues = _apply_unrecoverable_override(self._deterministic_checks(state).issues, state)
        issues = _apply_analyst_failure_override(issues, state)
        return QAResult(
            passed=not any(issue.severity == "blocker" for issue in issues),
            issues=issues,
        )

    def _deterministic_checks(self, state: WorkflowState) -> QAResult:
        issues: list[QAIssue] = []
        now = datetime.now(UTC)
        sources_by_id = {
            source.id: source
            for result in state.raw_collections.values()
            for source in result.sources
        }

        # Demo feedback loop trigger
        force_blocker = bool(state.feedback_signals.get("force_pricing_blocker"))
        if force_blocker and state.retry_counts.get("collector", 0) == 0:
            issues.append(
                QAIssue(
                    severity="blocker",
                    target_agent="CollectorAgent",
                    failed_field="pricing.entry_price",
                    message="演示反馈闭环：定价字段被故意置为不完整。",
                    code="pricing_demo_blocker",
                )
            )

        for name, profile in state.structured_profiles.items():
            # Core layer: source_ids missing → blocker
            if not profile.source_ids:
                issues.append(
                    QAIssue(
                        severity="blocker",
                        target_agent="CollectorAgent",
                        target_competitor=name,
                        failed_field="source_ids",
                        message="竞品画像缺少引用来源。",
                        code="citation_missing",
                    )
                )

            unknown_rate = _feature_unknown_rate(profile)
            if unknown_rate is None:
                raw_entry = state.raw_collections.get(name)
                has_real_sources = raw_entry is not None and RawCollectionResult.model_validate(
                    raw_entry
                ).has_real_sources()
                issues.append(
                    QAIssue(
                        severity="blocker",
                        target_agent="CollectorAgent",
                        target_competitor=name,
                        failed_field="feature_tree",
                        message="功能树缺少可比较的结构化行。",
                        code="feature_tree_missing",
                        retryable=not has_real_sources,
                    )
                )
            elif unknown_rate > _MAX_FEATURE_UNKNOWN_RATE:
                issues.append(
                    QAIssue(
                        severity="blocker",
                        target_agent="CollectorAgent",
                        target_competitor=name,
                        failed_field="feature_tree",
                        message=(
                            f"功能树未知字段占比 {unknown_rate:.0%}，超过 "
                            f"{_MAX_FEATURE_UNKNOWN_RATE:.0%} 的质量阈值。"
                        ),
                        code="feature_tree_sparse",
                    )
                )

            tiers = profile.pricing.get("tiers") or []
            if not tiers:
                issues.append(
                    QAIssue(
                        severity="blocker",
                        target_agent="CollectorAgent",
                        target_competitor=name,
                        failed_field="pricing",
                        message="缺少可验证的定价档位。",
                        code="pricing_missing",
                    )
                )
            elif _pricing_lacks_factual_source(tiers, sources_by_id):
                # Pricing is a hard fact: a price backed only by user reviews/feedback
                # isn't trustworthy. Block until an official or commercial source is
                # collected (a collection gap, hence retryable) rather than letting
                # review chatter stand in for a published price.
                issues.append(
                    QAIssue(
                        severity="blocker",
                        target_agent="CollectorAgent",
                        target_competitor=name,
                        failed_field="pricing.source_ids",
                        message=(
                            "定价仅由用户反馈支撑，缺少官网或商业来源。"
                        ),
                        code="pricing_source_weak",
                    )
                )

            if not profile.user_personas:
                issues.append(
                    QAIssue(
                        severity="blocker",
                        target_agent="CollectorAgent",
                        target_competitor=name,
                        failed_field="user_personas",
                        message="缺少用户画像。",
                        code="persona_missing",
                    )
                )

            non_empty_swot = sum(
                1
                for quadrant in ("strengths", "weaknesses", "opportunities", "threats")
                if profile.swot.get(quadrant)
            )
            if non_empty_swot < _MIN_SWOT_NON_EMPTY_QUADRANTS:
                issues.append(
                    QAIssue(
                        severity="blocker",
                        target_agent="CollectorAgent",
                        target_competitor=name,
                        failed_field="swot",
                        message=(
                            f"SWOT 仅填充 {non_empty_swot} 个象限，至少需要 "
                            f"{_MIN_SWOT_NON_EMPTY_QUADRANTS} 个象限。"
                        ),
                        code="swot_incomplete",
                    )
                )

            # Core sections whose rows carry no citation at all. A warning (not a
            # blocker) so the run still completes, but the report's quality panel
            # can surface that a core section leans on uncited claims.
            uncited_sections = _core_sections_missing_citations(profile)
            if uncited_sections:
                issues.append(
                    QAIssue(
                        severity="warning",
                        target_agent="AnalystAgent",
                        target_competitor=name,
                        failed_field="core.source_ids",
                        message=(
                            "核心章节存在未引用字段："
                            f"{', '.join(uncited_sections)}。"
                        ),
                        code="core_citation_missing",
                        retryable=False,
                    )
                )

            # Per-competitor source count check (PRD §六 5.4: ≥5 independent sources)
            raw = state.raw_collections.get(name)
            if raw is not None:
                if len(raw.sources) < _MIN_SOURCES_PER_COMPETITOR:
                    issues.append(
                        QAIssue(
                            severity="blocker",
                            target_agent="CollectorAgent",
                            target_competitor=name,
                            failed_field="sources",
                            message=(
                                f"仅采集到 {len(raw.sources)} 条来源，至少需要 "
                                f"{_MIN_SOURCES_PER_COMPETITOR} 条独立来源。"
                            ),
                            code="source_count_low",
                        )
                    )

                # Source staleness: fetched_at > 2 years ago → warning
                stale = [
                    s
                    for s in raw.sources
                    if (now - s.fetched_at).days > _SOURCE_STALENESS_YEARS * 365
                ]
                if stale:
                    issues.append(
                        QAIssue(
                            severity="warning",
                            target_agent="CollectorAgent",
                            target_competitor=name,
                            failed_field="sources.fetched_at",
                            message=(
                                f"{len(stale)} 条来源超过 "
                                f"{_SOURCE_STALENESS_YEARS} 年，可能过时。"
                            ),
                            code="source_stale",
                            retryable=False,
                        )
                    )

        # Extension layer: source_ids missing → also blocker (PRD §六 5.4)
        for finding in state.extension_findings:
            if not finding.source_ids:
                issues.append(
                    QAIssue(
                        severity="blocker",
                        target_agent="AnalystAgent",
                        target_competitor=finding.competitor_name,
                        failed_field=f"extension_findings[{finding.dimension_id}].source_ids",
                        message="扩展维度结论缺少引用来源。",
                        code="extension_citation_missing",
                    )
                )

        # Survey checks
        for name, survey in state.survey_results.items():
            if not survey.evidence:
                issues.append(
                    QAIssue(
                        severity="blocker",
                        target_agent="SurveyTool",
                        target_competitor=name,
                        failed_field="survey.evidence",
                        message="调研结果缺少证据。",
                        code="survey_evidence_missing",
                    )
                )
                continue
            evidence_by_id = {item.id: item for item in survey.evidence}
            for insight in survey.insights:
                if not insight.evidence_ids:
                    issues.append(
                        QAIssue(
                            severity="blocker",
                            target_agent="SurveyTool",
                            target_competitor=name,
                            failed_field=f"survey.insights[{insight.question_id}].evidence_ids",
                            message="调研洞察缺少 evidence_ids。",
                            code="survey_insight_evidence_missing",
                        )
                    )
                    continue
                real_evidence = [
                    evidence_by_id[evidence_id]
                    for evidence_id in insight.evidence_ids
                    if evidence_id in evidence_by_id
                    and evidence_by_id[evidence_id].source_type
                    in {"user_uploaded_primary", "published_survey", "public_review"}
                ]
                if not real_evidence:
                    issues.append(
                        QAIssue(
                            severity="warning",
                            target_agent="SurveyTool",
                            target_competitor=name,
                            failed_field=f"survey.insights[{insight.question_id}].evidence_ids",
                            message="调研洞察仅由 AI 模拟证据支撑。",
                            code="survey_ai_simulated_only",
                            retryable=False,
                        )
                    )
            evidence_count = len(survey.evidence)
            simulated_count = sum(1 for e in survey.evidence if e.source_type == "ai_simulated")
            if simulated_count / evidence_count > 0.6:
                issues.append(
                    QAIssue(
                        severity="warning",
                        target_agent="SurveyTool",
                        target_competitor=name,
                        failed_field="survey.source_breakdown",
                        message="调研结果主要依赖 AI 模拟证据。",
                        code="survey_ai_simulated_majority",
                        retryable=False,
                    )
                )

        return QAResult(
            passed=not any(i.severity == "blocker" for i in issues),
            issues=issues,
        )


_UNRECOVERABLE_ERROR_HINTS = (
    "429",
    "432",
    "quota",
    "usage limit",
    "too many requests",
    "rate limit",
    "401",
    "403",
    "unauthorized",
    "no search providers configured",
)


def _parse_llm_retryable(issue: dict) -> bool:
    """Default an LLM-emitted issue's ``retryable`` when the model omits it.

    Retry is the most expensive path (a full re-collection round per attempt), so
    a CollectorAgent blocker must explicitly opt in to a retry — otherwise we
    default conservative and skip it. Other agents keep the permissive default.
    """
    if "retryable" in issue:
        return bool(issue["retryable"])
    return str(issue.get("target_agent", "AnalystAgent")) != "CollectorAgent"


def _apply_unrecoverable_override(issues: list[QAIssue], state: WorkflowState) -> list[QAIssue]:
    """Force CollectorAgent blockers non-retryable when a retry can't help.

    A collector retry only helps when the failure was transient. When a competitor
    got zero real sources and the errors point at quota/auth exhaustion, every retry
    hits the same wall (a full re-collection round + LLM cost for nothing). This runs
    over the *combined* LLM + deterministic issues so an LLM-emitted blocker that
    insists ``retryable=True`` for a dead competitor can't slip a wasted retry past
    the gate. A global blocker (no target_competitor) is downgraded only when every
    collected competitor is unrecoverable — otherwise a retry could still help one.
    """
    unrecoverable = {
        name for name, raw in state.raw_collections.items() if _collection_unrecoverable(raw)
    }
    all_unrecoverable = bool(state.raw_collections) and unrecoverable == set(state.raw_collections)
    for issue in issues:
        if issue.severity != "blocker" or issue.target_agent != "CollectorAgent":
            continue
        # The scripted demo blocker drives a fixed feedback-loop retry; it must keep
        # firing even when live collection is exhausted, so the override never mutes it.
        if issue.code == "pricing_demo_blocker":
            continue
        if issue.target_competitor in unrecoverable or (
            issue.target_competitor is None and all_unrecoverable
        ):
            issue.retryable = False
    return issues


def _apply_analyst_failure_override(issues: list[QAIssue], state: WorkflowState) -> list[QAIssue]:
    """Re-target a competitor's CollectorAgent blockers to the Analyst when the real
    cause is a failed extraction, not a collection gap.

    A competitor that was collected with real sources but came back with an empty
    profile (Analyst extraction failed, e.g. truncated DeepSeek JSON) would otherwise
    raise CollectorAgent blockers that route back to re-collection — which returns the
    same good sources and fails identically, burning a full retry round per attempt.
    Re-collection can't fix an extraction failure, so these blockers are pinned to
    AnalystAgent and made non-retryable; the gap is then surfaced in the report.
    """
    failed = _analyst_failed_competitors(state)
    if not failed:
        return issues
    for issue in issues:
        if (
            issue.severity == "blocker"
            and issue.target_agent == "CollectorAgent"
            and issue.target_competitor in failed
        ):
            issue.target_agent = "AnalystAgent"
            issue.retryable = False
    return issues


def _analyst_failed_competitors(state: WorkflowState) -> set[str]:
    """Competitors that have real collected sources yet an empty profile.

    Empty ``source_ids`` is the signature of a totally failed extraction (a real
    extraction always stamps the ids it cited); paired with real sources it means
    collection succeeded but structuring did not.
    """
    failed: set[str] = set()
    for name, profile in state.structured_profiles.items():
        if profile.source_ids:
            continue
        raw = state.raw_collections.get(name)
        if raw is None:
            continue
        if RawCollectionResult.model_validate(raw).has_real_sources():
            failed.add(name)
    return failed


def _collection_unrecoverable(raw: RawCollectionResult | None) -> bool:
    if raw is None or raw.has_real_sources():
        return False
    if raw.unrecoverable:
        return True
    error_text = " ".join(
        error for error in raw.errors if not error.startswith("dropped_irrelevant:")
    ).lower()
    return any(hint in error_text for hint in _UNRECOVERABLE_ERROR_HINTS)


def _issue_code(failed_field: str) -> str:
    field = failed_field.lower()
    if "pricing" in field:
        return "pricing_missing"
    if "swot" in field:
        return "swot_incomplete"
    if "feature" in field:
        return "feature_tree_sparse"
    if "source" in field or "citation" in field:
        return "citation_missing"
    if "survey" in field:
        return "survey_quality_issue"
    if "persona" in field:
        return "persona_missing"
    return "quality_issue"


_PRICING_FACTUAL_SOURCE = frozenset({"official", "commercial"})


def _pricing_lacks_factual_source(
    tiers: list[dict],
    sources_by_id: dict[str, SourceCitation],
) -> bool:
    """True when pricing tiers cite sources but none are official/commercial.

    Returns False when no cited source resolves (that's a missing-citation
    concern surfaced elsewhere, not a "review-only pricing" violation), so the
    gate fires only on the specific case it owns.
    """
    resolved = [
        sources_by_id[source_id]
        for tier in tiers
        for source_id in (tier.get("source_ids") or [])
        if source_id in sources_by_id
    ]
    if not resolved:
        return False
    return not any(
        source.type in _PRICING_FACTUAL_SOURCE or source.category in _PRICING_FACTUAL_SOURCE
        for source in resolved
    )


def _rows_missing_source_ids(rows: object) -> bool:
    return isinstance(rows, list) and any(
        isinstance(row, dict) and not (row.get("source_ids") or []) for row in rows
    )


def _core_sections_missing_citations(profile: StructuredCompetitorProfile) -> list[str]:
    """Names of core sections with at least one row that cites no source."""
    sections: list[str] = []
    if _rows_missing_source_ids(profile.feature_tree.get("rows")):
        sections.append("feature_tree")
    if _rows_missing_source_ids(profile.user_personas):
        sections.append("user_personas")
    swot_items = [
        item
        for quadrant in ("strengths", "weaknesses", "opportunities", "threats")
        for item in (profile.swot.get(quadrant) or [])
    ]
    if _rows_missing_source_ids(swot_items):
        sections.append("swot")
    return sections


def _feature_unknown_rate(profile: StructuredCompetitorProfile) -> float | None:
    rows = profile.feature_tree.get("rows") or []
    cells: list[dict] = []
    for row in rows:
        row_cells = row.get("cells") or []
        cells.extend(
            cell
            for cell in row_cells
            if str(cell.get("competitor", profile.competitor_name)).lower()
            == profile.competitor_name.lower()
        )
    if not cells:
        return None
    unknown = sum(1 for cell in cells if str(cell.get("status", "")).lower() == "unknown")
    return unknown / len(cells)


def _fact_check_samples(state: WorkflowState) -> list[dict]:
    source_text = {
        source.id: {
            "title": source.title,
            "snippet": source.snippet,
            "content_sample": (source.raw_content or "")[:1000],
        }
        for result in state.raw_collections.values()
        for source in result.sources
    }
    samples: list[dict] = []
    for name, profile in state.structured_profiles.items():
        source_ids = [source_id for source_id in profile.source_ids if source_id in source_text]
        if not source_ids:
            continue
        samples.append({
            "competitor": name,
            "field": "pricing",
            "claim": profile.pricing,
            "sources": {source_id: source_text[source_id] for source_id in source_ids[:3]},
        })
        samples.append({
            "competitor": name,
            "field": "swot",
            "claim": profile.swot,
            "sources": {source_id: source_text[source_id] for source_id in source_ids[:3]},
        })
    return samples[:_MAX_FACT_CHECK_SAMPLES]
