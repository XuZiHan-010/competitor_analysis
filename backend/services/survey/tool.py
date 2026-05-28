from collections import Counter
from collections.abc import Sequence

from graph.state import RawCollectionResult, WorkflowState
from schemas.survey import SurveyEvidence, SurveyInsight, SurveyResult


class SurveyTool:
    def run(self, state: WorkflowState) -> dict[str, SurveyResult]:
        if not state.scope_contract.user_research_plan.enabled:
            return {}
        questions = state.scope_contract.user_research_plan.questionnaire
        return {
            name: self._run_competitor(result, questions)
            for name, result in state.raw_collections.items()
        }

    def _run_competitor(
        self,
        result: RawCollectionResult,
        questions: Sequence[object],
    ) -> SurveyResult:
        evidence = self._collect_public_voice(result)
        if not evidence:
            evidence = self._simulate_evidence(result.competitor_name, questions)
        insights = self._aggregate_insights(result.competitor_name, evidence)
        return SurveyResult(
            competitor_name=result.competitor_name,
            evidence=evidence,
            insights=insights,
            source_breakdown=dict(Counter(item.source_type for item in evidence)),
        )

    def _collect_public_voice(self, result: RawCollectionResult) -> list[SurveyEvidence]:
        evidence: list[SurveyEvidence] = []
        for source in result.sources:
            if source.category != "user_feedback" and source.type not in {
                "app_review",
                "public_review",
            }:
                continue
            evidence.append(
                SurveyEvidence(
                    source_type="public_review",
                    source_id=source.id,
                    content=source.snippet,
                    redacted=True,
                )
            )
        return evidence

    def _simulate_evidence(
        self,
        competitor_name: str,
        questions: Sequence[object],
    ) -> list[SurveyEvidence]:
        question_count = max(len(questions), 1)
        return [
            SurveyEvidence(
                source_type="ai_simulated",
                source_id=None,
                content=(
                    f"AI simulated respondent signal for {competitor_name}; "
                    f"covers {question_count} planned research questions."
                ),
                redacted=True,
            )
        ]

    def _aggregate_insights(
        self,
        competitor_name: str,
        evidence: list[SurveyEvidence],
    ) -> list[SurveyInsight]:
        evidence_ids = [str(item.id) for item in evidence]
        simulated_count = sum(1 for item in evidence if item.source_type == "ai_simulated")
        support = "weak" if simulated_count == len(evidence) else "supported"
        return [
            SurveyInsight(
                summary=f"{competitor_name} user voice signals are available for report synthesis.",
                evidence_ids=evidence_ids,
                source_support=support,
            )
        ]
