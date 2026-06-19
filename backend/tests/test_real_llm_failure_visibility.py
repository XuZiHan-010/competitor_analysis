import asyncio

import pytest

from agents.analyst import AnalystAgent
from graph.state import RawCollectionResult, WorkflowState
from schemas.scope import CompetitorCandidate, ScopeDimension, TaskScopeContract
from schemas.source import SourceCitation
from services.llm import LLMClient
from services.llm.client import _json_content_snippets
from settings import get_settings


def _workflow_state() -> WorkflowState:
    scope = TaskScopeContract(
        user_brief="Compare AI coding tools",
        intent_mode="list",
        competitors=[CompetitorCandidate(name="Trae", source="nl_extracted")],
        dimensions=[
            ScopeDimension(
                id="core.feature_tree",
                title="Feature tree",
                intent="Compare features",
                layer="core",
                order=1,
            )
        ],
    )
    return WorkflowState(
        task_id=scope.id,
        run_id=scope.id,
        scope_contract=scope,
        raw_collections={
            "Trae": RawCollectionResult(
                competitor_name="Trae",
                sources=[
                    SourceCitation(
                        id="src_tavily_deadbeef_001",
                        type="media",
                        category="media",
                        title="Trae feature source",
                        snippet="Trae feature evidence.",
                        provider="tavily",
                    )
                ],
            )
        },
    )


def test_analyst_real_mode_llm_failure_does_not_return_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_llm(self: AnalystAgent, state: WorkflowState, llm: object) -> tuple:
        raise ValueError("bad json")

    monkeypatch.setenv("MOCK_LLM", "false")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(AnalystAgent, "_run_llm", fail_llm)

    async def run_agent() -> None:
        await AnalystAgent().run(_workflow_state())

    try:
        with pytest.raises(RuntimeError, match="AnalystAgent LLM failed"):
            asyncio.run(run_agent())
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_complete_json_retries_empty_and_invalid_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = LLMClient(get_settings())
    responses = iter(["", "{not-json", '{"ok": true}'])

    async def fake_json_text(
        *,
        provider: object,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        return next(responses)

    monkeypatch.setattr(client, "_complete_json_text", fake_json_text)

    assert await client.complete_json(
        provider="deepseek",
        model="deepseek-chat",
        messages=[{"role": "system", "content": "Return JSON."}],
    ) == {"ok": True}


@pytest.mark.asyncio
async def test_complete_json_raises_after_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    client = LLMClient(get_settings())

    async def fake_json_text(
        *,
        provider: object,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        return ""

    monkeypatch.setattr(client, "_complete_json_text", fake_json_text)

    with pytest.raises(RuntimeError, match="returned invalid JSON"):
        await client.complete_json(
            provider="deepseek",
            model="deepseek-chat",
            messages=[{"role": "system", "content": "Return JSON."}],
        )


@pytest.mark.asyncio
async def test_complete_json_repairs_malformed_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = LLMClient(get_settings())
    responses = iter(['{"name":"unterminated', '{"name":"fixed"}'])
    seen_messages: list[list[dict[str, str]]] = []

    async def fake_json_text(
        *,
        provider: object,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        seen_messages.append(messages)
        return next(responses)

    monkeypatch.setattr(client, "_complete_json_text", fake_json_text)

    assert await client.complete_json(
        provider="deepseek",
        model="deepseek-chat",
        messages=[{"role": "system", "content": "Return JSON."}],
        expected_shape='{"name":"string"}',
    ) == {"name": "fixed"}
    assert "Malformed JSON to repair" in seen_messages[1][1]["content"]


@pytest.mark.asyncio
async def test_complete_json_extracts_json_object_from_wrapped_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = LLMClient(get_settings())

    async def fake_json_text(
        *,
        provider: object,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        return '```json\n{"ok": true}\n```'

    monkeypatch.setattr(client, "_complete_json_text", fake_json_text)

    assert await client.complete_json(
        provider="deepseek",
        model="deepseek-chat",
        messages=[{"role": "system", "content": "Return JSON."}],
        repair_invalid=False,
    ) == {"ok": True}


@pytest.mark.asyncio
async def test_complete_json_rejects_non_object_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = LLMClient(get_settings())

    async def fake_json_text(
        *,
        provider: object,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        return "[]"

    monkeypatch.setattr(client, "_complete_json_text", fake_json_text)

    with pytest.raises(RuntimeError, match="JSON response must be an object"):
        await client.complete_json(
            provider="deepseek",
            model="deepseek-chat",
            messages=[{"role": "system", "content": "Return JSON."}],
            repair_invalid=False,
        )


@pytest.mark.asyncio
async def test_complete_json_raises_when_repair_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = LLMClient(get_settings())
    responses = iter(['{"bad":"json', '{still-bad'] * 3)

    async def fake_json_text(
        *,
        provider: object,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        return next(responses)

    monkeypatch.setattr(client, "_complete_json_text", fake_json_text)

    with pytest.raises(RuntimeError, match="returned invalid JSON"):
        await client.complete_json(
            provider="deepseek",
            model="deepseek-chat",
            messages=[{"role": "system", "content": "Return JSON."}],
        )


def test_json_log_snippets_do_not_include_full_response() -> None:
    content = "a" * 220 + "SECRET_FULL_RESPONSE" + "z" * 220

    snippets = _json_content_snippets(content)

    assert snippets["response_length"] == len(content)
    assert snippets["response_head"] == "a" * 180
    assert snippets["response_tail"] == "z" * 180
    assert "SECRET_FULL_RESPONSE" not in snippets["response_head"]
    assert "SECRET_FULL_RESPONSE" not in snippets["response_tail"]
