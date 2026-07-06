from collections.abc import Sequence
from typing import Any

import structlog

from schemas.scope import ScopeDimension
from schemas.survey import Questionnaire, SurveyQuestion
from services.llm import LLMClient
from settings import get_settings

logger = structlog.get_logger(__name__)


class QuestionnaireDesigner:
    async def design(
        self,
        *,
        competitor: str,
        dimensions: Sequence[ScopeDimension],
        existing_questionnaire: Questionnaire | None,
    ) -> Questionnaire:
        dimension_intent = self._dimension_intent(dimensions)
        if existing_questionnaire is not None:
            return existing_questionnaire.model_copy(
                update={
                    "competitor": competitor,
                    "dimension_intent": dimension_intent,
                }
            )
        settings = get_settings()
        llm = LLMClient(settings)
        if llm.enabled and settings.openai_api_key:
            try:
                return await self._design_with_llm(
                    competitor=competitor,
                    dimension_intent=dimension_intent,
                    llm=llm,
                )
            except Exception:
                logger.warning("questionnaire_llm_failed_falling_back", exc_info=True)
        return self._design_fallback(competitor=competitor, dimension_intent=dimension_intent)

    async def _design_with_llm(
        self,
        *,
        competitor: str,
        dimension_intent: str,
        llm: LLMClient,
    ) -> Questionnaire:
        settings = get_settings()
        payload = await llm.complete_json(
            provider="openai",
            model=settings.scoping_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是竞品分析 SurveyTool 的问卷设计器 questionnaire_designer。"
                        "返回严格的 JSON，包含 design_rationale 和 5-10 个 questions。"
                        "每个 question 必须包含 id、text、type(open|multiple_choice|scale)、"
                        "options 和 intent。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Competitor: {competitor}\n"
                        f"Dimension intent: {dimension_intent}\n"
                        "Design concise Chinese survey/interview questions for user research."
                    ),
                },
            ],
        )
        questions = self._questions_from_payload(payload.get("questions", []))
        if len(questions) < 5:
            return self._design_fallback(
                competitor=competitor,
                dimension_intent=dimension_intent,
            )
        return Questionnaire(
            competitor=competitor,
            dimension_intent=dimension_intent,
            questions=questions[:10],
            design_rationale=str(
                payload.get(
                    "design_rationale",
                    "LLM 生成问卷，覆盖采用动机、满意度、竞品感知和改进机会。",
                )
            ),
        )

    def _questions_from_payload(self, questions_payload: Any) -> list[SurveyQuestion]:
        if not isinstance(questions_payload, list):
            return []
        questions: list[SurveyQuestion] = []
        for index, item in enumerate(questions_payload, start=1):
            if not isinstance(item, dict):
                continue
            question_type = item.get("type", "open")
            if question_type not in {"open", "multiple_choice", "scale"}:
                question_type = "open"
            options = item.get("options")
            questions.append(
                SurveyQuestion(
                    id=str(item.get("id") or f"sq_{index:03d}"),
                    text=str(item.get("text") or item.get("question") or ""),
                    type=question_type,
                    options=options if isinstance(options, list) else None,
                    intent=str(item.get("intent") or "捕捉用户声音。"),
                )
            )
        return [question for question in questions if question.text.strip()]

    def _design_fallback(self, *, competitor: str, dimension_intent: str) -> Questionnaire:
        questions = [
            SurveyQuestion(
                id="sq_001",
                text=f"你选择或放弃 {competitor} 的首要原因是什么？",
                type="open",
                intent="识别采用动机、流失原因和高频痛点。",
            ),
            SurveyQuestion(
                id="sq_002",
                text=f"你对 {competitor} 的价格、功能、服务满意度如何？",
                type="scale",
                options=["1", "2", "3", "4", "5"],
                intent="量化用户对核心体验维度的满意度。",
            ),
            SurveyQuestion(
                id="sq_003",
                text=f"与同类产品相比，{competitor} 最明显的优势是什么？",
                type="open",
                intent="提炼可进入 SWOT 和差异化分析的用户感知。",
            ),
            SurveyQuestion(
                id="sq_004",
                text=f"你希望 {competitor} 下一步优先改善什么？",
                type="open",
                intent="捕捉产品机会点和未满足需求。",
            ),
            SurveyQuestion(
                id="sq_005",
                text="你更接近哪类使用者？",
                type="multiple_choice",
                options=["个人轻度用户", "团队协作用户", "管理/采购决策者", "其他"],
                intent="为后续 persona 推断提供基础分层。",
            ),
        ]
        return Questionnaire(
            competitor=competitor,
            dimension_intent=dimension_intent,
            questions=questions,
            design_rationale=(
                "问卷覆盖采用动机、满意度、竞品感知、改进机会和用户分层，"
                "可同时服务核心画像、SWOT 与用户声音扩展维度。"
            ),
        )

    def _dimension_intent(self, dimensions: Sequence[ScopeDimension]) -> str:
        enabled = [dimension.intent for dimension in dimensions if dimension.enabled]
        return "；".join(enabled[:4]) if enabled else "识别用户声音和竞品体验差异。"
