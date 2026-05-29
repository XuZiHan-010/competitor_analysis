from pydantic import BaseModel

from schemas.source import SourceCitation
from schemas.survey import Questionnaire, SurveyEvidence
from services.search.providers import SearchProvider

_RESEARCH_KEYWORDS = {
    "survey",
    "report",
    "research",
    "study",
    "customer satisfaction",
    "user satisfaction",
    "nps",
    "review",
    "调研",
    "报告",
    "研究",
    "满意度",
    "用户反馈",
    "消费者洞察",
}


class ExistingSurveyFindResult(BaseModel):
    evidence: list[SurveyEvidence]
    sources: list[SourceCitation]
    rejected_count: int = 0


class ExistingSurveyFinder:
    def __init__(self, search: SearchProvider | None = None) -> None:
        self._search = search

    async def find(
        self,
        *,
        competitor: str,
        questionnaire: Questionnaire,
        max_results: int = 3,
    ) -> ExistingSurveyFindResult:
        if self._search is None:
            return ExistingSurveyFindResult(evidence=[], sources=[])
        query = " OR ".join(
            [
                f'"{competitor}" "user survey" report',
                f'"{competitor}" "customer satisfaction" research',
                f'"{competitor}" 用户 调研 报告 满意度',
            ]
        )
        sources = await self._search.search(query, max_results=max(max_results * 2, 6))
        if not sources:
            return ExistingSurveyFindResult(evidence=[], sources=[])
        questions = questionnaire.questions
        evidence: list[SurveyEvidence] = []
        accepted_sources: list[SourceCitation] = []
        rejected_count = 0
        for source in sources:
            if not self._looks_like_research_source(source):
                rejected_count += 1
                continue
            quote = source.snippet or source.title or source.raw_content or ""
            if not quote:
                rejected_count += 1
                continue
            accepted_sources.append(source)
            evidence.append(
                SurveyEvidence(
                    question_id=questions[len(evidence) % len(questions)].id,
                    source_type="published_survey",
                    source_id=source.id,
                    raw_quote=quote,
                    persona_inferred=None,
                )
            )
            if len(evidence) >= max_results:
                break
        return ExistingSurveyFindResult(
            evidence=evidence,
            sources=accepted_sources,
            rejected_count=rejected_count,
        )

    def _looks_like_research_source(self, source: SourceCitation) -> bool:
        haystack = " ".join(
            [
                source.title,
                source.snippet,
                source.raw_content or "",
                str(source.url or ""),
            ]
        ).lower()
        return any(keyword.lower() in haystack for keyword in _RESEARCH_KEYWORDS)
