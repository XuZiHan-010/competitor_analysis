from datetime import UTC, datetime

import structlog

from graph.state import QAIssue, QAResult, WorkflowState
from services.agents.decorators import traced_node
from services.llm import LLMClient
from settings import get_settings

_MIN_SOURCES_PER_COMPETITOR = 5
_SOURCE_STALENESS_YEARS = 2

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
        payload = await llm.complete_json(
            provider="openai",
            model=settings.qa_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are QAAgent. Return JSON: {passed:boolean, issues:[{severity,"
                        "target_agent,target_competitor,failed_field,message,retryable}]}."
                    ),
                },
                {
                    "role": "user",
                    "content": (f"Profiles: {profiles_payload}\n" f"Sources: {sources_payload}"),
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
