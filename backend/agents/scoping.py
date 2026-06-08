from typing import Any, Literal

import structlog

from schemas.scope import (
    CompetitorCandidate,
    ScopeDimension,
    ScopingDraft,
    ScopingRequest,
    TaskScopeContract,
    UserResearchPlan,
)
from schemas.survey import Questionnaire, SurveyQuestion
from services.agents.decorators import traced_node
from services.llm import LLMClient
from settings import get_settings

logger = structlog.get_logger(__name__)

IntentMode = Literal["list", "intent", "mixed"]


def _coerce_intent_mode(value: object) -> IntentMode:
    if value == "list":
        return "list"
    if value == "mixed":
        return "mixed"
    return "intent"


SCOPING_SYSTEM_PROMPT = (
    "You are ScopingAgent. Return JSON matching this exact schema:\n"
    "{\n"
    '  "named_in_brief": ["每个在 brief 原文中逐字出现的产品/品牌/竞品名"],\n'
    '  "intent_mode": "list" | "intent" | "mixed",\n'
    '  "competitors": [\n'
    '    {"name": "X", "source": "nl_extracted", "reason": "为何纳入"},\n'
    '    {"name": "Y", "source": "ai_recommended", "reason": "同价位/同人群"}\n'
    "  ],\n"
    '  "extension_dimensions": [\n'
    '    {"title": "维度名称", "intent": "一句话说明分析意图"}\n'
    "  ],\n"
    '  "clarification_questions": ["question1"],\n'
    '  "rationale": "why these competitors and dimensions"\n'
    "}\n"
    "Work in THREE ordered steps:\n"
    "STEP 1 — Extract entities FIRST. Put into named_in_brief EVERY "
    "product/brand/company name that appears LITERALLY in the brief. "
    "Names after 对比/比较/分析/vs separated by 、，,/和 are competitor "
    "names EVEN IF the brief also states a research focus (e.g. "
    "'重点关注…定价'). Research-focus wording does NOT cancel an explicit "
    "name. Empty array only if the brief truly names none.\n"
    "STEP 2 — Classify intent_mode:\n"
    "- 'list': brief names 2+ products and does NOT ask for more. A "
    "research focus does NOT downgrade this to 'intent'.\n"
    "- 'intent': brief describes a research question with NO product name "
    "(or only one).\n"
    "- 'mixed': brief names 1+ products AND explicitly asks for more "
    "('再补几个' / '还有哪些类似产品').\n"
    "STEP 3 — Choose competitors. EVERY name in named_in_brief MUST appear "
    "in competitors with source='nl_extracted' (mandatory in ALL modes).\n"
    "- 'list': ONLY the named ones, source='nl_extracted'; no "
    "ai_recommended, no padding.\n"
    "- 'intent': 3-5 competitors, all source='ai_recommended'.\n"
    "- 'mixed': the named ones (nl_extracted) + enough ai_recommended to "
    "reach 3-5.\n"
    "Examples:\n"
    "- '对比 Trae、Cursor、GitHub Copilot 在 AI 编程辅助上的差异，重点关注"
    "开发者体验与定价' → named_in_brief=['Trae','Cursor','GitHub Copilot'], "
    "intent_mode='list', competitors = those three as nl_extracted, "
    "nothing else.\n"
    "- '帮我研究短视频电商赛道有哪些值得对标的玩家' → named_in_brief=[], "
    "intent_mode='intent', 3-5 ai_recommended.\n"
    "STEP 4 — Brainstorm extension_dimensions. The report ALWAYS ships 4 "
    "FIXED core chapters (功能树 / 定价模型 / 用户画像 / SWOT); never "
    "repeat or rephrase those here. Reason like a senior analyst about THIS "
    "competitive set and its industry, and propose 2-4 ADDITIONAL dimensions "
    "that surface the non-obvious, decision-relevant angles an expert would "
    "add beyond the 4 cores. Turn any research focus stated in the brief "
    "(e.g. '重点关注…') into a dimension. Return [] ONLY when the brief is "
    "genuinely too narrow to warrant any — do NOT default to empty out of "
    "caution. Tailor every item to the actual competitors; do NOT emit these "
    "examples verbatim:\n"
    "- 短视频平台(抖音/快手/视频号) → 内容生态与创作者激励 / 算法推荐与分发 / "
    "商业化与电商闭环 / 增长与留存\n"
    "- AI 编程工具 → 模型与上下文能力 / IDE 与生态集成 / 数据隐私与合规\n"
    "- 协作办公(Notion/Lark) → 集成生态与开放 API / 权限与企业治理\n"
    "CRITICAL: each competitors item must be an object with keys exactly "
    "'name', 'source', 'reason'; source is exactly 'nl_extracted' or "
    "'ai_recommended'. extension_dimensions keys must be exactly 'title' "
    "and 'intent'. Do NOT list the target product itself, nor its regional "
    "rebrands or overseas variants, as competitors (analyzing 飞书 → do NOT "
    "include Lark). At most 5 competitors; extension_dimensions should hold "
    "2-4 tailored items (hard cap 4)."
)


class ScopingAgent:
    @traced_node(
        agent_name="ScopingAgent",
        node_name="run_scoping",
        prompt="Extract competitors and dimensions from user brief, return ScopingDraft.",
    )
    async def run(
        self,
        request: ScopingRequest,
        *,
        trace_context: object | None = None,
    ) -> ScopingDraft:
        settings = get_settings()
        llm = LLMClient(settings)
        if llm.enabled and settings.openai_api_key:
            try:
                return await self._run_llm(request, llm)
            except Exception:
                logger.warning("scoping_llm_failed_falling_back", exc_info=True)
        return self._run_fallback(request)

    async def _run_llm(self, request: ScopingRequest, llm: LLMClient) -> ScopingDraft:
        settings = get_settings()
        payload = await llm.complete_json(
            provider="openai",
            model=settings.scoping_model,
            messages=[
                {"role": "system", "content": SCOPING_SYSTEM_PROMPT},
                self._build_user_message(request),
            ],
        )
        intent_mode = _coerce_intent_mode(payload.get("intent_mode"))
        raw_competitors = payload.get("competitors", [])
        competitors: list[CompetitorCandidate] = []
        for item in raw_competitors[:5]:
            if isinstance(item, dict):
                name = str(item.get("name", item.get("product", item.get("title", "")))).strip()
                raw_source = item.get("source")
                reason = item.get("reason") or item.get("rationale")
            else:
                name = str(item).strip()
                raw_source, reason = None, None
            if not name:
                continue
            source: Literal["nl_extracted", "ai_recommended"] = (
                "ai_recommended" if raw_source == "ai_recommended" else "nl_extracted"
            )
            competitors.append(
                CompetitorCandidate(
                    name=name,
                    source=source,
                    rationale=str(reason).strip() if reason else "LLM scoped competitor",
                )
            )
        competitors, intent_mode = self._anchor_named_competitors(
            competitors, request, payload, intent_mode
        )
        # The 4 cores always ship; extension dimensions are the LLM's value-add.
        # A weak model (debug-tier gpt-4o-mini) sometimes returns [] despite the
        # prompt forbidding it — never let the outline ship without extensions:
        # give the model one forceful second chance, then a deterministic floor.
        extension_raw = self._coerce_extension_list(payload.get("extension_dimensions"))
        if not extension_raw:
            extension_raw = await self._retry_extensions(request, llm)
        if not extension_raw:
            extension_raw = self._floor_extensions()
        dimensions = self._core_dimensions()
        for index, dimension in enumerate(extension_raw[:4], start=5):
            if isinstance(dimension, dict):
                title = str(
                    dimension.get("title")
                    or dimension.get("name")
                    or f"扩展维度 {index - 4}"
                ).strip()
                intent = str(
                    dimension.get("intent")
                    or dimension.get("description")
                    or "按任务意图补充分析。"
                ).strip()
            else:
                title = str(dimension).strip() or f"扩展维度 {index - 4}"
                intent = "按任务意图补充分析。"
            dimensions.append(
                ScopeDimension(
                    id=f"ext.{index - 4}",
                    title=title,
                    intent=intent,
                    layer="extension",
                    order=index,
                    source="ai_suggested",
                )
            )
        scope_contract = TaskScopeContract(
            user_brief=request.user_brief,
            intent_mode=intent_mode,
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

    def _build_user_message(self, request: ScopingRequest) -> dict[str, str]:
        previous_draft_info = (
            request.previous_draft.model_dump(mode="json") if request.previous_draft else None
        )
        return {
            "role": "user",
            "content": (
                f"Brief: {request.user_brief}\n"
                f"Known competitors: {request.known_competitors}\n"
                f"Clarifications: {request.clarifications}\n"
                f"Previous draft: {previous_draft_info}"
            ),
        }

    @staticmethod
    def _coerce_extension_list(value: object) -> list[Any]:
        return value if isinstance(value, list) else []

    async def _retry_extensions(self, request: ScopingRequest, llm: LLMClient) -> list[Any]:
        settings = get_settings()
        payload = await llm.complete_json(
            provider="openai",
            model=settings.scoping_model,
            messages=[
                {"role": "system", "content": SCOPING_SYSTEM_PROMPT},
                self._build_user_message(request),
                {
                    "role": "user",
                    "content": (
                        "你上一次返回的 extension_dimensions 是空数组。请重新审视这组竞品"
                        "与所在行业，像资深分析师那样给出 2-4 个量身定制、对决策有用的扩展维度，"
                        "禁止返回空。只返回与之前相同 schema 的 JSON。"
                    ),
                },
            ],
        )
        return self._coerce_extension_list(payload.get("extension_dimensions"))

    def _floor_extensions(self) -> list[Any]:
        # Last resort when the model returns [] twice: two angles that hold for
        # virtually any competitive set, so the outline is never empty of
        # extensions. Kept deliberately generic; a stronger demo model (gpt-4.1)
        # rarely reaches here.
        return [
            {
                "title": "用户声音与口碑",
                "intent": "聚合公开评论、社媒口碑与典型抱怨，定位体验落差。",
            },
            {
                "title": "竞争格局与差异化定位",
                "intent": "梳理各竞品的市场定位、目标人群差异与护城河。",
            },
        ]

    def _anchor_named_competitors(
        self,
        competitors: list[CompetitorCandidate],
        request: ScopingRequest,
        payload: dict[str, object],
        intent_mode: IntentMode,
    ) -> tuple[list[CompetitorCandidate], IntentMode]:
        # The LLM occasionally drops or substitutes products the user explicitly
        # named, hallucinating a generic list instead. Re-anchor on deterministic
        # ground truth: any name the user supplied as a chip, or that appears
        # verbatim in the brief, MUST survive regardless of what the model returned.
        raw_named = payload.get("named_in_brief")
        named_in_brief = [str(n).strip() for n in raw_named] if isinstance(raw_named, list) else []
        brief_lower = request.user_brief.lower()
        must_keep = [name for name in request.known_competitors if name.strip()]
        must_keep += [name for name in named_in_brief if name and name.lower() in brief_lower]

        existing_lower = {c.name.lower() for c in competitors}
        anchored: list[CompetitorCandidate] = []
        for name in must_keep:
            key = name.lower()
            if key in existing_lower:
                continue
            existing_lower.add(key)
            anchored.append(
                CompetitorCandidate(name=name, source="nl_extracted", rationale="brief 点名")
            )
        # Named competitors lead; model recommendations follow, capped at 5 total.
        competitors = (anchored + competitors)[:5]

        # If the brief explicitly named products, it is not pure 'intent' mode —
        # repair the classification the model may have gotten wrong.
        if must_keep and intent_mode == "intent":
            has_recommended = any(c.source == "ai_recommended" for c in competitors)
            intent_mode = "mixed" if has_recommended else "list"
        return competitors, intent_mode

    def _run_fallback(self, request: ScopingRequest) -> ScopingDraft:
        # No LLM available: we can only honor competitors the caller already named
        # (chips on regenerate, or the brief on first call). We do NOT pad the list,
        # matching the list-mode contract. With no names there is nothing to scope,
        # so we raise — the frontend has a graceful degrade path for this.
        competitors = self._competitors_from_request(request)
        if not competitors:
            raise ValueError(
                "fallback ScopingAgent cannot extract competitors without an LLM; "
                "provide known_competitors"
            )
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
            intent_mode="list" if request.known_competitors else "intent",
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
            questionnaire=Questionnaire(
                competitor="all",
                dimension_intent="聚合用户声音、公开评论和问卷/访谈信号。",
                questions=[
                    SurveyQuestion(
                        id="sq_001",
                        text="你选择该产品的首要原因是什么？",
                        type="open",
                        intent="识别购买或采用产品的核心触发因素。",
                    ),
                    SurveyQuestion(
                        id="sq_002",
                        text="你对价格、功能、服务三项的满意度如何？",
                        type="scale",
                        options=["1", "2", "3", "4", "5"],
                        intent="量化用户对关键体验维度的满意度。",
                    ),
                ],
                design_rationale="覆盖采用动机与满意度，作为用户研究模块的基础提纲。",
            ),
        )

    def _competitors_from_request(self, request: ScopingRequest) -> list[CompetitorCandidate]:
        names = [name.strip() for name in request.known_competitors if name.strip()]
        return [
            CompetitorCandidate(
                name=name,
                source="nl_extracted",
                rationale="Extracted from user-provided competitor list.",
            )
            for name in names[:5]
        ]
