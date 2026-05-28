from schemas.scope import (
    CompetitorCandidate,
    ScopeDimension,
    ScopingDraft,
    ScopingRequest,
    SurveyQuestion,
    TaskScopeContract,
    UserResearchPlan,
)
from services.llm import LLMClient
from settings import get_settings


class ScopingAgent:
    async def run(self, request: ScopingRequest) -> ScopingDraft:
        settings = get_settings()
        llm = LLMClient(settings)
        if llm.enabled and settings.openai_api_key:
            try:
                return await self._run_llm(request, llm)
            except Exception:
                pass
        return self._run_fallback(request)

    async def _run_llm(self, request: ScopingRequest, llm: LLMClient) -> ScopingDraft:
        settings = get_settings()
        previous_draft_info = (
            request.previous_draft.model_dump(mode="json") if request.previous_draft else None
        )
        payload = await llm.complete_json(
            provider="openai",
            model=settings.scoping_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are ScopingAgent. Return strict JSON with competitors, "
                        "extension_dimensions, clarification_questions, and rationale. "
                        "Use 3-5 competitors and at most 4 extension dimensions."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Brief: {request.user_brief}\n"
                        f"Known competitors: {request.known_competitors}\n"
                        f"Clarifications: {request.clarifications}\n"
                        f"Previous draft: {previous_draft_info}"
                    ),
                },
            ],
        )
        competitor_names = [
            str(name).strip() for name in payload.get("competitors", []) if str(name).strip()
        ][:5]
        extension_dimensions = payload.get("extension_dimensions", [])
        competitors = [
            CompetitorCandidate(
                name=name,
                source="nl_extracted" if index == 0 else "ai_recommended",
                rationale="LLM scoped competitor",
            )
            for index, name in enumerate(competitor_names)
        ]
        while len(competitors) < 3:
            competitors.append(
                CompetitorCandidate(
                    name=f"Competitor {len(competitors) + 1}",
                    source="ai_recommended",
                    rationale="Filled to satisfy 3 competitor minimum",
                )
            )
        dimensions = self._core_dimensions()
        for index, dimension in enumerate(extension_dimensions[:4], start=5):
            dimensions.append(
                ScopeDimension(
                    id=f"ext.{index - 4}",
                    title=str(dimension.get("title", f"扩展维度 {index - 4}")),
                    intent=str(dimension.get("intent", "按任务意图补充分析。")),
                    layer="extension",
                    order=index,
                    source="ai_suggested",
                )
            )
        scope_contract = TaskScopeContract(
            user_brief=request.user_brief,
            intent_mode="mixed" if request.known_competitors else "intent",
            competitors=competitors,
            dimensions=dimensions,
            user_research_plan=self._default_survey_plan(),
        )
        return ScopingDraft(
            scope_contract=scope_contract,
            clarification_questions=[
                str(q) for q in payload.get("clarification_questions", [])[:3]
            ],
            rationale=str(payload.get("rationale", "LLM generated scoping draft.")),
        )

    def _run_fallback(self, request: ScopingRequest) -> ScopingDraft:
        competitors = self._competitors_from_request(request)
        dimensions = self._core_dimensions()
        dimensions.append(
            ScopeDimension(
                id="ext.user_voice",
                title="用户声音",
                intent="聚合评论、公开反馈和用户研究信号。",
                layer="extension",
                order=5,
                source="ai_suggested",
            )
        )
        scope_contract = TaskScopeContract(
            user_brief=request.user_brief,
            intent_mode="mixed" if request.known_competitors else "intent",
            competitors=competitors,
            dimensions=dimensions,
            user_research_plan=self._default_survey_plan(),
        )
        return ScopingDraft(
            scope_contract=scope_contract,
            clarification_questions=["这份报告更偏产品规划还是汇报决策？"],
            rationale=(
                "Fallback ScopingAgent created a stable baseline contract "
                "for local/CI integration."
            ),
        )

    def _core_dimensions(self) -> list[ScopeDimension]:
        return [
            ScopeDimension(
                id="core.feature_tree",
                title="功能树",
                intent="梳理核心能力、差异化功能和功能覆盖。",
                layer="core",
                order=1,
                locked=True,
                schema_ref="FeatureTree",
            ),
            ScopeDimension(
                id="core.pricing",
                title="定价模型",
                intent="比较价格层级、套餐结构和付费门槛。",
                layer="core",
                order=2,
                locked=True,
                schema_ref="PricingModel",
            ),
            ScopeDimension(
                id="core.persona",
                title="用户画像",
                intent="识别目标用户、使用场景和典型痛点。",
                layer="core",
                order=3,
                locked=True,
                schema_ref="UserPersona",
            ),
            ScopeDimension(
                id="core.swot",
                title="SWOT",
                intent="总结优势、劣势、机会和威胁。",
                layer="core",
                order=4,
                locked=True,
                schema_ref="SWOT",
            ),
        ]

    def _default_survey_plan(self) -> UserResearchPlan:
        return UserResearchPlan(
            enabled=True,
            questionnaire=[
                SurveyQuestion(
                    id="q1",
                    text="你选择该产品的首要原因是什么？",
                    question_type="free_text",
                ),
                SurveyQuestion(
                    id="q2",
                    text="你对价格、功能、服务三项的满意度如何？",
                    question_type="scale",
                    options=["1", "2", "3", "4", "5"],
                ),
            ],
            interview_outline=["购买或采用产品的触发事件", "最不满意的体验节点"],
        )

    def _competitors_from_request(self, request: ScopingRequest) -> list[CompetitorCandidate]:
        names = [name.strip() for name in request.known_competitors if name.strip()]
        if not names:
            names = ["Notion", "Lark", "Airtable"]
        while len(names) < 3:
            names.append(f"Competitor {len(names) + 1}")
        return [
            CompetitorCandidate(
                name=name,
                source="nl_extracted" if index == 0 else "ai_recommended",
                rationale="S0 mock recommendation; replace with LLM scoping in S1.",
            )
            for index, name in enumerate(names[:5])
        ]
