import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from agents.scoping import ScopingAgent
from schemas.scope import ScopingRequest


def test_create_scoping_draft_list_mode_keeps_named_competitors(
    auth_client_factory: Callable[[str], TestClient],
) -> None:
    client = auth_client_factory("eric@example.com")
    response = client.post(
        "/api/tasks/scoping",
        json={
            "user_brief": "分析 Notion 和 Lark 的协作能力",
            "known_competitors": ["Notion", "Lark"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    contract = data["scope_contract"]
    # list mode: keep exactly the named competitors, no AI padding to 3-5.
    assert contract["intent_mode"] == "list"
    assert [c["name"] for c in contract["competitors"]] == ["Notion", "Lark"]
    assert all(c["source"] == "nl_extracted" for c in contract["competitors"])
    assert contract["user_research_plan"]["enabled"] is True
    questionnaire = contract["user_research_plan"]["questionnaire"]
    assert questionnaire["design_rationale"]
    assert questionnaire["questions"][0]["intent"]

    task_id = contract["id"]
    saved_response = client.get(f"/api/tasks/scoping/drafts/{task_id}")
    assert saved_response.status_code == 200
    assert saved_response.json()["scope_contract"]["id"] == task_id


def test_create_scoping_draft_no_competitors_degrades(
    auth_client_factory: Callable[[str], TestClient],
) -> None:
    # Without an LLM (tests run MOCK_LLM=true) and with no named competitors,
    # the fallback cannot scope anything: return 422 so the frontend degrades.
    client = auth_client_factory("eric@example.com")
    response = client.post(
        "/api/tasks/scoping",
        json={"user_brief": "帮我看看短视频电商赛道"},
    )
    assert response.status_code == 422


def _fake_llm(payload: dict[str, object]) -> AsyncMock:
    llm = AsyncMock()
    llm.complete_json.return_value = payload
    return llm


def _fake_llm_seq(payloads: list[dict[str, object]]) -> AsyncMock:
    # Distinct payloads per successive complete_json call — used to exercise the
    # empty-extensions retry path (initial call vs. the forced second attempt).
    llm = AsyncMock()
    llm.complete_json.side_effect = payloads
    return llm


def test_anchor_reinjects_named_competitors_when_llm_drops_them() -> None:
    # The real LLM path: model hallucinated a generic list and dropped every
    # product the brief named. The deterministic guard must re-anchor them.
    llm = _fake_llm(
        {
            "intent_mode": "intent",
            "competitors": [
                {"name": "Tabnine", "source": "ai_recommended", "reason": "x"},
                {"name": "Kite", "source": "ai_recommended", "reason": "x"},
            ],
            "named_in_brief": ["Trae", "Cursor", "GitHub Copilot", "Foobar"],
            "extension_dimensions": [],
            "clarification_questions": [],
            "rationale": "...",
        }
    )
    request = ScopingRequest(
        user_brief="对比 Trae、Cursor、GitHub Copilot 在 AI 编程辅助上的差异",
        known_competitors=[],
    )
    draft = asyncio.run(ScopingAgent()._run_llm(request, llm))
    contract = draft.scope_contract
    names = [c.name for c in contract.competitors]

    for named in ("Trae", "Cursor", "GitHub Copilot"):
        assert named in names
        candidate = next(c for c in contract.competitors if c.name == named)
        assert candidate.source == "nl_extracted"
    # 'Foobar' is in named_in_brief but NOT verbatim in the brief → dropped.
    assert "Foobar" not in names
    # Brief named products → not pure 'intent'; ai_recommended also present → mixed.
    assert contract.intent_mode == "mixed"
    assert len(names) <= 5


def test_llm_extension_dimensions_are_mapped_and_capped() -> None:
    # The brainstormed extension dimensions from the model must land in the
    # contract as layer="extension"/source="ai_suggested", on top of the 4 fixed
    # cores, and be capped at 4 even if the model over-produces.
    llm = _fake_llm(
        {
            "intent_mode": "list",
            "competitors": [
                {"name": "抖音", "source": "nl_extracted", "reason": "x"},
                {"name": "快手", "source": "nl_extracted", "reason": "x"},
            ],
            "named_in_brief": ["抖音", "快手"],
            "extension_dimensions": [
                {"title": "内容生态与创作者激励", "intent": "评估创作者供给与激励。"},
                {"title": "算法推荐与分发", "intent": "对比推荐机制与流量分发。"},
                {"title": "商业化与电商闭环", "intent": "比较变现路径与电商闭环。"},
                {"title": "增长与留存", "intent": "看拉新与留存策略。"},
                {"title": "第五个会被截断", "intent": "超过上限应被丢弃。"},
            ],
            "clarification_questions": [],
            "rationale": "...",
        }
    )
    request = ScopingRequest(
        user_brief="对比 抖音、快手 的短视频生态",
        known_competitors=["抖音", "快手"],
    )
    draft = asyncio.run(ScopingAgent()._run_llm(request, llm))
    dimensions = draft.scope_contract.dimensions

    core = [d for d in dimensions if d.layer == "core"]
    extensions = [d for d in dimensions if d.layer == "extension"]
    assert len(core) == 4
    # over-production is capped at 4 ai_suggested extensions
    assert len(extensions) == 4
    assert all(d.source == "ai_suggested" for d in extensions)
    assert "内容生态与创作者激励" in [d.title for d in extensions]
    assert "第五个会被截断" not in [d.title for d in extensions]


def test_anchor_keeps_known_competitor_chips_on_regenerate() -> None:
    # Regenerate path: user-supplied chips must survive even if the model omits them.
    llm = _fake_llm(
        {
            "intent_mode": "list",
            "competitors": [{"name": "Cursor", "source": "nl_extracted", "reason": "x"}],
            "named_in_brief": [],
            "extension_dimensions": [],
            "clarification_questions": [],
            "rationale": "...",
        }
    )
    request = ScopingRequest(
        user_brief="比较几款 AI 编程工具",
        known_competitors=["Trae", "Cursor"],
    )
    draft = asyncio.run(ScopingAgent()._run_llm(request, llm))
    names = [c.name for c in draft.scope_contract.competitors]
    assert "Trae" in names
    assert names.count("Cursor") == 1


def test_single_named_competitor_is_padded_to_minimum() -> None:
    # User named exactly one competitor: the model returns it alone (list-ish),
    # so the deterministic floor must pad with ai_recommended peers to reach 3-5
    # and reclassify the result as 'mixed'.
    first: dict[str, object] = {
        "intent_mode": "list",
        "competitors": [{"name": "Trae", "source": "nl_extracted", "reason": "x"}],
        "named_in_brief": ["Trae"],
        "extension_dimensions": [
            {"title": "模型与上下文能力", "intent": "对比底层模型与上下文窗口。"},
            {"title": "IDE 与生态集成", "intent": "评估编辑器集成深度与插件生态。"},
        ],
        "clarification_questions": [],
        "rationale": "...",
    }
    padding: dict[str, object] = {
        "competitors": [
            {"name": "Cursor", "source": "ai_recommended", "reason": "同赛道"},
            {"name": "GitHub Copilot", "source": "ai_recommended", "reason": "同赛道"},
        ],
    }
    llm = _fake_llm_seq([first, padding])
    request = ScopingRequest(user_brief="分析 Trae", known_competitors=["Trae"])
    draft = asyncio.run(ScopingAgent()._run_llm(request, llm))
    contract = draft.scope_contract
    names = [c.name for c in contract.competitors]

    assert "Trae" in names
    assert len(names) >= 3
    trae = next(c for c in contract.competitors if c.name == "Trae")
    assert trae.source == "nl_extracted"
    assert any(c.source == "ai_recommended" for c in contract.competitors)
    assert contract.intent_mode == "mixed"


def test_intent_mode_competitors_padded_when_llm_returns_too_few() -> None:
    # Pure intent (no named products) where the model under-delivers: a single
    # ai_recommended must be topped up to >=3, staying 'intent'.
    first: dict[str, object] = {
        "intent_mode": "intent",
        "competitors": [{"name": "抖音", "source": "ai_recommended", "reason": "龙头"}],
        "named_in_brief": [],
        "extension_dimensions": [
            {"title": "内容生态与创作者激励", "intent": "评估创作者供给与激励。"},
        ],
        "clarification_questions": [],
        "rationale": "...",
    }
    padding: dict[str, object] = {
        "competitors": [
            {"name": "快手", "source": "ai_recommended", "reason": "同赛道"},
            {"name": "视频号", "source": "ai_recommended", "reason": "同赛道"},
        ],
    }
    llm = _fake_llm_seq([first, padding])
    request = ScopingRequest(user_brief="帮我看看短视频电商赛道", known_competitors=[])
    draft = asyncio.run(ScopingAgent()._run_llm(request, llm))
    contract = draft.scope_contract

    assert len(contract.competitors) >= 3
    assert all(c.source == "ai_recommended" for c in contract.competitors)
    assert contract.intent_mode == "intent"


def test_empty_extension_dimensions_retry_succeeds() -> None:
    # A weak model returns [] on the first pass; the forced retry produces real
    # dimensions, which must land in the contract instead of the floor.
    first: dict[str, object] = {
        "intent_mode": "list",
        "competitors": [
            {"name": "Trae", "source": "nl_extracted", "reason": "x"},
            {"name": "Cursor", "source": "nl_extracted", "reason": "x"},
        ],
        "named_in_brief": ["Trae", "Cursor"],
        "extension_dimensions": [],
        "clarification_questions": [],
        "rationale": "...",
    }
    retry: dict[str, object] = {
        "extension_dimensions": [
            {"title": "模型与上下文能力", "intent": "对比底层模型与上下文窗口。"},
            {"title": "IDE 与生态集成", "intent": "评估编辑器集成深度与插件生态。"},
        ],
    }
    llm = _fake_llm_seq([first, retry])
    request = ScopingRequest(
        user_brief="对比 Trae、Cursor 的 AI 编程能力",
        known_competitors=["Trae", "Cursor"],
    )
    draft = asyncio.run(ScopingAgent()._run_llm(request, llm))

    extensions = [d for d in draft.scope_contract.dimensions if d.layer == "extension"]
    titles = [d.title for d in extensions]
    assert "模型与上下文能力" in titles
    assert "IDE 与生态集成" in titles
    assert all(d.source == "ai_suggested" for d in extensions)
    assert llm.complete_json.call_count == 2


def test_echoed_core_dimensions_are_dropped_then_retried() -> None:
    # The 抖音 quick-query failure mode: gpt-4o-mini ignores STEP 4 and returns the
    # 4 fixed cores verbatim as "extensions". They must be dropped, the forced retry
    # produces genuinely new dimensions, and no core title leaks into extensions.
    echoed: dict[str, object] = {
        "intent_mode": "list",
        "competitors": [
            {"name": "抖音", "source": "nl_extracted", "reason": "x"},
            {"name": "快手", "source": "nl_extracted", "reason": "x"},
        ],
        "named_in_brief": ["抖音", "快手"],
        "extension_dimensions": [
            {"title": "功能树", "intent": "分析各产品的功能模块与特色"},
            {"title": "定价模型", "intent": "比较各产品的付费策略"},
            {"title": "用户画像", "intent": "识别目标用户"},
            {"title": "SWOT", "intent": "总结优劣势"},
        ],
        "clarification_questions": [],
        "rationale": "...",
    }
    retry: dict[str, object] = {
        "extension_dimensions": [
            {"title": "内容生态与创作者激励", "intent": "评估创作者供给与激励。"},
            {"title": "算法推荐与分发", "intent": "对比推荐机制与流量分发。"},
        ],
    }
    llm = _fake_llm_seq([echoed, retry])
    request = ScopingRequest(
        user_brief="对比 抖音、快手 的短视频生态",
        known_competitors=["抖音", "快手"],
    )
    draft = asyncio.run(ScopingAgent()._run_llm(request, llm))

    extensions = [d for d in draft.scope_contract.dimensions if d.layer == "extension"]
    titles = [d.title for d in extensions]
    core_titles = {"功能树", "定价模型", "用户画像", "SWOT"}
    assert core_titles.isdisjoint(titles)
    assert "内容生态与创作者激励" in titles
    assert all(d.source == "ai_suggested" for d in extensions)
    # echoed cores dropped → empty → forced retry fired
    assert llm.complete_json.call_count == 2


def test_empty_extension_dimensions_falls_back_to_floor() -> None:
    # Both the initial call and the retry return [] — the deterministic floor
    # must guarantee the outline still ships with extension dimensions.
    empty: dict[str, object] = {
        "intent_mode": "list",
        "competitors": [
            {"name": "记事本A", "source": "nl_extracted", "reason": "x"},
            {"name": "记事本B", "source": "nl_extracted", "reason": "x"},
        ],
        "named_in_brief": ["记事本A", "记事本B"],
        "extension_dimensions": [],
        "clarification_questions": [],
        "rationale": "...",
    }
    llm = _fake_llm_seq([empty, empty])
    request = ScopingRequest(
        user_brief="比较 记事本A、记事本B",
        known_competitors=["记事本A", "记事本B"],
    )
    draft = asyncio.run(ScopingAgent()._run_llm(request, llm))

    extensions = [d for d in draft.scope_contract.dimensions if d.layer == "extension"]
    titles = [d.title for d in extensions]
    assert len(extensions) >= 1
    assert "用户声音与口碑" in titles
    assert all(d.source == "ai_suggested" for d in extensions)
    assert llm.complete_json.call_count == 2
