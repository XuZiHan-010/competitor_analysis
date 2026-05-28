import asyncio
from unittest.mock import AsyncMock

from agents.collector import CollectorAgent
from graph.state import WorkflowState
from schemas.scope import CompetitorCandidate, ScopeDimension, TaskScopeContract
from schemas.source import SourceCitation
from settings import get_settings


def _state() -> WorkflowState:
    scope = TaskScopeContract(
        user_brief="Compare collaboration tools",
        intent_mode="list",
        competitors=[
            CompetitorCandidate(name="Notion", source="nl_extracted"),
            CompetitorCandidate(name="Lark", source="nl_extracted"),
            CompetitorCandidate(name="Airtable", source="nl_extracted"),
        ],
        dimensions=[
            ScopeDimension(
                id="core.feature_tree",
                title="功能树",
                intent="Compare features",
                layer="core",
                order=1,
            )
        ],
    )
    return WorkflowState(task_id=scope.id, run_id=scope.id, scope_contract=scope)


def test_collector_real_collection_uses_search_and_app_reviews() -> None:
    search = AsyncMock()
    search.search.return_value = [
        SourceCitation(
            id="src_real",
            type="media",
            category="media",
            url="https://example.com",
            title="Real search",
            snippet="Real source",
            provider="test",
        )
    ]
    app_reviews = AsyncMock()
    app_reviews.fetch_reviews.return_value = [
        SourceCitation(
            id="src_app",
            type="app_review",
            category="user_feedback",
            url=None,
            title="App review",
            snippet="Review",
            provider="test",
        )
    ]
    fetcher = AsyncMock()
    fetcher.fetch_page.return_value = type(
        "Fetched",
        (),
        {
            "skipped": False,
            "url": "https://example.com",
            "title": "Fetched",
            "content": "Fetched content",
        },
    )()
    results = asyncio.run(
        CollectorAgent()._run_real_collection(_state(), search, app_reviews, fetcher)
    )
    assert len(results) == 3
    # 1 enabled dimension × 3 competitors = 3 search calls
    assert search.search.call_count == 3
    assert app_reviews.fetch_reviews.call_count == 3
    # 1 url-bearing source × 3 competitors = 3 fetch calls
    assert fetcher.fetch_page.call_count == 3
    first_result = next(iter(results.values()))
    assert len(first_result.sources) == 2


def test_settings_cache_can_be_cleared_for_env_switches() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
