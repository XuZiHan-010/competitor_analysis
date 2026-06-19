from collections import Counter
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from inspect import isawaitable
from time import perf_counter
from typing import Any, Literal, TypeVar, cast

import structlog

from graph.state import RawCollectionResult, WorkflowState
from schemas.survey import (
    DistributionHandle,
    Questionnaire,
    SurveyEvidence,
    SurveyInsight,
    SurveyResponse,
    SurveyResult,
    TargetPersona,
)
from schemas.traces import AgentTrace
from services.agents.decorators import _estimate_tokens
from services.llm import LLMClient
from services.llm.usage import record_degradation
from services.survey.distributors import SimulatedDistributor, SurveyDistributor
from services.survey.existing_survey_finder import ExistingSurveyFinder, ExistingSurveyFindResult
from services.survey.persona_inferrer import PersonaInferrer
from services.survey.questionnaire_designer import QuestionnaireDesigner

T = TypeVar("T")
_MISSING = object()


def _safe_int(value: Any, default: int) -> int:
    """LLM 偶尔把 ``frequency`` 返回成词（实测 'high'）；安全转换，
    避免 ``int('high')`` 崩溃后整段 survey 降级。"""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text.isdigit():
            return int(text)
        return {"high": 3, "medium": 2, "low": 1}.get(text, default)
    return default


def _safe_str_list(value: Any) -> list[str]:
    """LLM 偶尔把 ``representative_quotes`` 返回成字符串而非数组（实测被截断的
    '用户满'）；切片 ``[:3]`` 会得到前 3 个字符再塞进 ``list[str]`` 字段，触发
    ValidationError。统一兜底为 ``list[str]``，避免整段 survey 降级。"""
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _safe_confidence(value: Any) -> Literal["high", "medium", "low"]:
    """LLM 偶尔把 ``confidence`` 返回成 'Medium'/'高' 等；映射回 Literal 三档，
    否则 Pydantic 校验失败导致整段 survey 降级。"""
    text = str(value).strip().lower()
    if text in {"high", "高"}:
        return "high"
    if text in {"medium", "中"}:
        return "medium"
    return "low"


logger = structlog.get_logger(__name__)


class SurveyTool:
    def __init__(
        self,
        *,
        designer: QuestionnaireDesigner | None = None,
        existing_survey_finder: ExistingSurveyFinder | None = None,
        persona_inferrer: PersonaInferrer | None = None,
        distributor: SurveyDistributor | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._designer = designer or QuestionnaireDesigner()
        self._existing_survey_finder = existing_survey_finder or ExistingSurveyFinder()
        self._persona_inferrer = persona_inferrer or PersonaInferrer()
        self._distributor = distributor or SimulatedDistributor()
        self._llm_client = llm_client

    async def run(
        self,
        state: WorkflowState,
        *,
        trace_context: Any | None = None,
    ) -> dict[str, SurveyResult]:
        if not state.scope_contract.user_research_plan.enabled:
            return {}
        results: dict[str, SurveyResult] = {}
        for name, result in state.raw_collections.items():
            results[name] = await self._run_competitor(
                state,
                result,
                trace_context=trace_context,
            )
        return results

    async def _run_competitor(
        self,
        state: WorkflowState,
        result: RawCollectionResult,
        *,
        trace_context: Any | None,
    ) -> SurveyResult:
        async def design_call() -> Questionnaire:
            return await self._designer.design(
                competitor=result.competitor_name,
                dimensions=state.scope_contract.dimensions,
                existing_questionnaire=state.scope_contract.user_research_plan.questionnaire,
            )

        questionnaire: Questionnaire = await self._run_stage(
            trace_context=trace_context,
            stage="survey.stage1.designer",
            competitor=result.competitor_name,
            input_payload={
                "dimensions": [dimension.id for dimension in state.scope_contract.dimensions],
                "has_existing_questionnaire": (
                    state.scope_contract.user_research_plan.questionnaire is not None
                ),
            },
            provider_impl=self._designer.__class__.__name__,
            call=design_call,
        )

        async def existing_call() -> ExistingSurveyFindResult:
            return await self._existing_survey_finder.find(
                competitor=result.competitor_name,
                questionnaire=questionnaire,
            )

        empty_existing = ExistingSurveyFindResult(evidence=[], sources=[])
        existing_result: ExistingSurveyFindResult = await self._run_stage(
            trace_context=trace_context,
            stage="survey.stage2a.existing",
            competitor=result.competitor_name,
            input_payload={"questionnaire_id": questionnaire.id},
            provider_impl=self._existing_survey_finder.__class__.__name__,
            call=existing_call,
            fallback=empty_existing,
        )
        existing_source_ids = {source.id for source in result.sources}
        result.sources.extend(
            source for source in existing_result.sources if source.id not in existing_source_ids
        )
        uploaded_evidence = self._uploaded_evidence(state, questionnaire)

        def public_voice_call() -> list[SurveyEvidence]:
            return self._collect_public_voice(result, questionnaire)

        public_voice: list[SurveyEvidence] = await self._run_stage(
            trace_context=trace_context,
            stage="survey.stage2b.voice",
            competitor=result.competitor_name,
            input_payload={"source_count": len(result.sources)},
            provider_impl="RawCollectionResult",
            call=public_voice_call,
        )
        evidence = [*uploaded_evidence, *existing_result.evidence, *public_voice]

        def persona_call() -> list[TargetPersona]:
            return self._persona_inferrer.infer(result)

        target_personas: list[TargetPersona] = await self._run_stage(
            trace_context=trace_context,
            stage="survey.stage3a.persona",
            competitor=result.competitor_name,
            input_payload={"source_count": len(result.sources)},
            provider_impl=self._persona_inferrer.__class__.__name__,
            call=persona_call,
        )

        def distribute_call() -> DistributionHandle:
            return self._distributor.distribute(
                questionnaire=questionnaire,
                target_personas=target_personas,
                sample_size=max(len(target_personas), 1),
            )

        distribution: DistributionHandle = await self._run_stage(
            trace_context=trace_context,
            stage="survey.stage3b.distribute",
            competitor=result.competitor_name,
            input_payload={
                "questionnaire_id": questionnaire.id,
                "target_persona_count": len(target_personas),
            },
            provider_impl=self._distributor.__class__.__name__,
            call=distribute_call,
        )

        def collect_call() -> list[SurveyResponse]:
            return self._distributor.collect_responses(distribution)

        responses: list[SurveyResponse] = await self._run_stage(
            trace_context=trace_context,
            stage="survey.stage3c.collect",
            competitor=result.competitor_name,
            input_payload={"distribution_id": distribution.id},
            provider_impl=self._distributor.__class__.__name__,
            call=collect_call,
        )
        if not evidence:
            evidence = self._simulate_evidence(questionnaire, responses)

        async def aggregate_call() -> list[SurveyInsight]:
            return await self._aggregate_insights(evidence, questionnaire, result.competitor_name)

        insights: list[SurveyInsight] = await self._run_stage(
            trace_context=trace_context,
            stage="survey.stage4.aggregate",
            competitor=result.competitor_name,
            input_payload={"evidence_count": len(evidence)},
            provider_impl=self.__class__.__name__,
            call=aggregate_call,
        )
        return SurveyResult(
            competitor=result.competitor_name,
            dimension_intent=questionnaire.dimension_intent,
            questionnaire=questionnaire,
            target_personas=target_personas,
            distribution=distribution,
            responses=responses,
            evidence=evidence,
            insights=insights,
            coverage_note=self._coverage_note(evidence),
            source_breakdown=dict(Counter(item.source_type for item in evidence)),
        )

    def _collect_public_voice(
        self,
        result: RawCollectionResult,
        questionnaire: Questionnaire,
    ) -> list[SurveyEvidence]:
        evidence: list[SurveyEvidence] = []
        questions = questionnaire.questions
        feedback_sources = [
            s
            for s in result.sources
            if s.category == "user_feedback" or s.type in {"app_review", "public_review"}
        ]
        for idx, source in enumerate(feedback_sources):
            evidence.append(
                SurveyEvidence(
                    question_id=questions[idx % len(questions)].id,
                    source_type="public_review",
                    source_id=source.id,
                    raw_quote=source.snippet,
                    persona_inferred="公开评论用户",
                )
            )
        return evidence

    def _uploaded_evidence(
        self,
        state: WorkflowState,
        questionnaire: Questionnaire,
    ) -> list[SurveyEvidence]:
        if not state.uploaded_survey_evidence:
            return []
        questions = questionnaire.questions
        return [
            item.model_copy(update={"question_id": questions[i % len(questions)].id})
            for i, item in enumerate(state.uploaded_survey_evidence)
        ]

    def _simulate_evidence(
        self,
        questionnaire: Questionnaire,
        responses: list[SurveyResponse],
    ) -> list[SurveyEvidence]:
        if not responses:
            return []
        # Rotate through all simulated respondents instead of pinning the first
        # one, otherwise every question quotes the same answer text and the
        # insights section reads as one line repeated N times.
        evidence: list[SurveyEvidence] = []
        for i, question in enumerate(questionnaire.questions):
            response = responses[i % len(responses)]
            evidence.append(
                SurveyEvidence(
                    question_id=question.id,
                    source_type="ai_simulated",
                    source_id=f"ai_simulated:{response.id}:{question.id}",
                    raw_quote=response.answers.get(question.id, ""),
                    persona_inferred=response.persona.label,
                )
            )
        return evidence

    async def _aggregate_insights(
        self,
        evidence: list[SurveyEvidence],
        questionnaire: Questionnaire,
        competitor: str,
    ) -> list[SurveyInsight]:
        if self._llm_client and self._llm_client.enabled:
            try:
                return await self._aggregate_insights_llm(evidence, questionnaire, competitor)
            except Exception as exc:
                logger.warning(
                    "survey_aggregate_llm_failed_falling_back",
                    competitor=competitor,
                    exc_info=True,
                )
                record_degradation(f"survey[{competitor}]: {type(exc).__name__}: {exc}")
        return self._aggregate_insights_fallback(evidence, questionnaire)

    async def _aggregate_insights_llm(
        self,
        evidence: list[SurveyEvidence],
        questionnaire: Questionnaire,
        competitor: str,
    ) -> list[SurveyInsight]:
        from settings import get_settings

        settings = get_settings()
        evidence_payload = [
            {
                "question_id": e.question_id,
                "source_type": e.source_type,
                "raw_quote": e.raw_quote,
                "persona_inferred": e.persona_inferred,
                "id": e.id,
            }
            for e in evidence
        ]
        questions_payload = [
            {"id": q.id, "text": q.text, "intent": q.intent}
            for q in questionnaire.questions
        ]
        payload = await self._llm_client.complete_json(  # type: ignore[union-attr]
            provider="openai",
            model=settings.qa_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a user research analyst. Synthesize survey evidence into "
                        "actionable insights for a Chinese report. Write every point and quote "
                        "summary in Simplified Chinese, even if the source evidence is English. "
                        "Return JSON: "
                        "{insights: [{question_id, point, frequency, representative_quotes, "
                        "evidence_ids, confidence}]}. "
                        "frequency must be an integer count of supporting evidence items. "
                        "confidence must be 'high'/'medium'/'low' based on evidence quality. "
                        "Every insight must include evidence_ids from the provided evidence."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Competitor: {competitor}\n"
                        f"Questions: {questions_payload}\n"
                        f"Evidence ({len(evidence)} items): {evidence_payload}"
                    ),
                },
            ],
        )
        evidence_by_id = {e.id: e for e in evidence}
        insights: list[SurveyInsight] = []
        for item in payload.get("insights", []):
            evidence_ids = [
                eid for eid in item.get("evidence_ids", []) if eid in evidence_by_id
            ]
            if not evidence_ids:
                # Assign evidence for matching question as fallback
                qid = str(item.get("question_id", ""))
                evidence_ids = [e.id for e in evidence if e.question_id == qid]
            insights.append(
                SurveyInsight(
                    question_id=str(item.get("question_id", "")),
                    point=str(item.get("point", "")),
                    frequency=_safe_int(item.get("frequency"), len(evidence_ids)),
                    representative_quotes=_safe_str_list(item.get("representative_quotes"))[:3],
                    evidence_ids=evidence_ids,
                    confidence=_safe_confidence(item.get("confidence")),
                )
            )
        return insights if insights else self._aggregate_insights_fallback(evidence, questionnaire)

    def _aggregate_insights_fallback(
        self,
        evidence: list[SurveyEvidence],
        questionnaire: Questionnaire,
    ) -> list[SurveyInsight]:
        insights: list[SurveyInsight] = []
        for question in questionnaire.questions:
            question_evidence = [item for item in evidence if item.question_id == question.id]
            if not question_evidence:
                continue
            real_count = sum(1 for item in question_evidence if item.source_type != "ai_simulated")
            real_ratio = real_count / len(question_evidence)
            confidence = "high" if real_ratio >= 0.7 else "medium" if real_ratio >= 0.3 else "low"
            insights.append(
                SurveyInsight(
                    question_id=question.id,
                    point=(
                        f"{question.intent}：基于 {len(question_evidence)} 条"
                        f"{'真实' if real_count else 'AI模拟'}用户声音信号进行分析。"
                    ),
                    frequency=len(question_evidence),
                    representative_quotes=[item.raw_quote for item in question_evidence[:3]],
                    evidence_ids=[item.id for item in question_evidence],
                    confidence=confidence,
                )
            )
        return insights

    def _coverage_note(self, evidence: list[SurveyEvidence]) -> str:
        if any(item.source_type != "ai_simulated" for item in evidence):
            return "包含公开用户反馈，可用于报告洞察；无上传一手数据时可信度仍需人工复核。"
        return "未找到公开用户反馈，当前为 AI 模拟兜底，报告页必须显示警示。"

    async def _run_stage(
        self,
        *,
        trace_context: Any | None,
        stage: str,
        competitor: str,
        input_payload: dict[str, Any],
        provider_impl: str,
        call: Callable[[], T | Awaitable[T]],
        fallback: T | object = _MISSING,
    ) -> T:
        started_at = datetime.now(UTC)
        start = perf_counter()
        try:
            maybe_output = call()
            output = await maybe_output if isawaitable(maybe_output) else maybe_output
        except Exception as exc:
            self._record_stage_trace(
                trace_context=trace_context,
                stage=stage,
                competitor=competitor,
                status="failed",
                input_payload=input_payload,
                output_payload={"error": exc.__class__.__name__},
                provider_impl=provider_impl,
                latency_ms=int((perf_counter() - start) * 1000),
                started_at=started_at,
                failure_reason=str(exc),
            )
            if fallback is not _MISSING:
                return cast(T, fallback)
            raise
        output_payload = _summarize_output(output)
        self._record_stage_trace(
            trace_context=trace_context,
            stage=stage,
            competitor=competitor,
            status="succeeded",
            input_payload=input_payload,
            output_payload=output_payload,
            provider_impl=provider_impl,
            latency_ms=int((perf_counter() - start) * 1000),
            started_at=started_at,
        )
        return output

    def _record_stage_trace(
        self,
        *,
        trace_context: Any | None,
        stage: str,
        competitor: str,
        status: str,
        input_payload: dict[str, Any],
        output_payload: dict[str, Any],
        provider_impl: str,
        latency_ms: int,
        started_at: datetime,
        failure_reason: str | None = None,
    ) -> None:
        if trace_context is None:
            return
        trace_context.record_trace(
            AgentTrace(
                task_run_id=trace_context.run_id,
                sequence_no=trace_context.next_sequence(),
                agent_name="SurveyTool",
                node_name=stage,
                status=cast(
                    Literal["started", "succeeded", "failed", "skipped", "retried"],
                    status,
                ),
                prompt=stage,
                input_payload={"competitor": competitor, **input_payload},
                output_payload=output_payload,
                tokens_in=_estimate_tokens(input_payload),
                tokens_out=_estimate_tokens(output_payload),
                latency_ms=latency_ms,
                decision_meta={
                    "provider_impl": provider_impl,
                    "failure_reason": failure_reason,
                },
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )
        )


def _summarize_output(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        return {
            "type": "list",
            "count": len(value),
            "output_summary": f"{len(value)} 项",
        }
    if hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json")
        return {
            "type": value.__class__.__name__,
            "summary": payload,
            "output_summary": _model_output_summary(value),
        }
    if isinstance(value, dict):
        keys = list(value.keys())
        return {
            "type": "dict",
            "keys": keys,
            "output_summary": f"dict / keys: {', '.join(str(key) for key in keys[:5])}",
        }
    return {
        "type": value.__class__.__name__,
        "value": repr(value),
        "output_summary": value.__class__.__name__,
    }


def _model_output_summary(value: Any) -> str:
    if isinstance(value, Questionnaire):
        return f"问卷 {value.id} / {len(value.questions)} 题"
    if isinstance(value, ExistingSurveyFindResult):
        return f"公开调研 {len(value.evidence)} 条证据 / {len(value.sources)} 条来源"
    if isinstance(value, DistributionHandle):
        return (
            f"分发 {value.id} / {len(value.target_personas)} 类 persona / "
            f"样本 {value.sample_size}"
        )
    if isinstance(value, SurveyResult):
        return (
            f"用户研究 {value.competitor} / {len(value.evidence)} 条证据 / "
            f"{len(value.insights)} 条洞察"
        )
    if hasattr(value, "model_fields"):
        fields = list(value.model_fields.keys())[:5]
        return f"{value.__class__.__name__} / keys: {', '.join(fields)}"
    return value.__class__.__name__


