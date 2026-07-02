from typing import Any

import pytest

from schemas.source import SourceCitation
from services.search.authority import grade_source_authority


def _src(
    sid: str,
    *,
    url: str | None = None,
    type_: str = "media",
    category: str = "media",
) -> SourceCitation:
    return SourceCitation(
        id=sid, type=type_, category=category, title="t", snippet="s", url=url, provider="tavily"
    )


class _FakeLLM:
    def __init__(
        self, grades: list[dict[str, Any]] | None = None, *, error: Exception | None = None
    ):
        self.enabled = True
        self._grades = grades or []
        self._error = error

    async def complete_json(self, **_: Any) -> dict[str, Any]:
        if self._error is not None:
            raise self._error
        return {"grades": self._grades}


@pytest.mark.asyncio
async def test_official_domain_and_authoritative_tld_grade_a() -> None:
    sources = [
        _src("s1", url="https://www.notion.so/pricing"),
        _src("s2", url="https://www.sec.gov/report"),
    ]

    graded = await grade_source_authority("Notion", sources, llm=None)

    tiers = {s.id: s.tier for s in graded}
    assert tiers["s1"] == "A"
    assert tiers["s2"] == "A"


@pytest.mark.asyncio
async def test_official_domain_media_source_recategorized_official() -> None:
    # Providers stamp official pricing pages as "media"; grading must upgrade the
    # product's own domain to category "official" so the pricing gate accepts it.
    source = _src("s1", url="https://www.notion.so/pricing", category="media")

    graded = await grade_source_authority("Notion", [source], llm=None)

    assert graded[0].tier == "A"
    assert graded[0].category == "official"


@pytest.mark.asyncio
async def test_non_official_media_category_left_untouched() -> None:
    # A lookalike / third-party media host must keep its media category, never bumped.
    source = _src("s1", url="https://notionfans.com/blog", category="media")

    graded = await grade_source_authority("Notion", [source], llm=None)

    assert graded[0].category == "media"


@pytest.mark.asyncio
async def test_ugc_host_and_review_type_grade_c() -> None:
    sources = [
        _src("s1", url="https://www.reddit.com/r/x"),
        _src("s2", type_="app_review"),
    ]

    graded = await grade_source_authority("Notion", sources, llm=None)

    tiers = {s.id: s.tier for s in graded}
    assert tiers["s1"] == "C"
    assert tiers["s2"] == "C"


@pytest.mark.asyncio
async def test_lookalike_domain_is_not_graded_official() -> None:
    # notionfans.com must NOT count as Notion's official domain (substring vs label).
    source = _src("s1", url="https://notionfans.com/blog")

    graded = await grade_source_authority("Notion", [source], llm=None)

    assert graded[0].tier == "C"  # ungraded by rules, no LLM → conservative C


@pytest.mark.asyncio
async def test_llm_grades_ambiguous_media_source() -> None:
    sources = [_src("s1", url="https://techcrunch.com/a")]
    llm = _FakeLLM([{"id": "s1", "tier": "B", "reason": "mainstream media"}])

    graded = await grade_source_authority("Notion", sources, llm=llm)  # type: ignore[arg-type]

    assert graded[0].tier == "B"


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_c() -> None:
    sources = [_src("s1", url="https://techcrunch.com/a")]
    llm = _FakeLLM(error=RuntimeError("deepseek down"))

    graded = await grade_source_authority("Notion", sources, llm=llm)  # type: ignore[arg-type]

    assert graded[0].tier == "C"


@pytest.mark.asyncio
async def test_output_sorted_a_b_c_and_preserves_count() -> None:
    sources = [
        _src("c1", url="https://reddit.com/x"),  # C by rule
        _src("a1", url="https://www.notion.so/docs"),  # A by rule
        _src("b1", url="https://techcrunch.com/a"),  # B by LLM
    ]
    llm = _FakeLLM([{"id": "b1", "tier": "B"}])

    graded = await grade_source_authority("Notion", sources, llm=llm)  # type: ignore[arg-type]

    assert [s.tier for s in graded] == ["A", "B", "C"]
    assert [s.id for s in graded] == ["a1", "b1", "c1"]
    assert len(graded) == len(sources)  # grading never drops sources
