from datetime import UTC, datetime

import structlog

from graph.state import QAIssue, QAResult, StructuredCompetitorProfile, WorkflowState
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
                        "target_agent,target_competitor,failed_field,message,retryable}]}. "
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
                retryable=bool(issue.get("retryable", True)),
            )
            for issue in payload.get("issues", [])
        ]
        # Always also run deterministic checks alongside LLM checks
        deterministic = self._deterministic_checks(state)
        all_issues = issues + deterministic.issues
        return QAResult(
            passed=not any(i.severity == "blocker" for i in all_issues),
            issues=all_issues,
        )

    def _run_fallback(self, state: WorkflowState) -> QAResult:
        issues = self._deterministic_checks(state).issues
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
                    message="Pricing is intentionally incomplete for feedback-loop demo.",
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
                        message="Profile has no citations.",
                    )
                )

            unknown_rate = _feature_unknown_rate(profile)
            if unknown_rate is None:
                issues.append(
                    QAIssue(
                        severity="blocker",
                        target_agent="CollectorAgent",
                        target_competitor=name,
                        failed_field="feature_tree",
                        message="Feature tree has no comparable rows.",
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
                            f"Feature tree unknown rate {unknown_rate:.0%} exceeds "
                            f"{_MAX_FEATURE_UNKNOWN_RATE:.0%}."
                        ),
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
                        message="Pricing tiers are missing.",
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
                            "Pricing is only supported by user feedback; "
                            "official or commercial source required."
                        ),
                    )
                )

            if not profile.user_personas:
                issues.append(
                    QAIssue(
                        severity="blocker",
                        target_agent="CollectorAgent",
                        target_competitor=name,
                        failed_field="user_personas",
                        message="User personas are missing.",
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
                            f"SWOT has {non_empty_swot} populated quadrants; "
                            f"need at least {_MIN_SWOT_NON_EMPTY_QUADRANTS}."
                        ),
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
                            "Core sections lack citations: "
                            f"{', '.join(uncited_sections)}."
                        ),
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
                                f"Only {len(raw.sources)} sources collected; "
                                f"need at least {_MIN_SOURCES_PER_COMPETITOR}."
                            ),
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
                                f"{len(stale)} source(s) older than "
                                f"{_SOURCE_STALENESS_YEARS} years."
                            ),
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
                        message="Extension finding has no citations.",
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
                        message="Survey result has no evidence.",
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
                            message="Survey insight has no evidence ids.",
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
                            message="Survey insight backed only by AI simulated evidence.",
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
                        message="Survey result relies mostly on AI simulated evidence.",
                        retryable=False,
                    )
                )

        return QAResult(
            passed=not any(i.severity == "blocker" for i in issues),
            issues=issues,
        )


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
