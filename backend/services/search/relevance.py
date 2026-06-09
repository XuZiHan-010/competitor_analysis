from dataclasses import dataclass

from schemas.source import SourceCitation
from services.llm import LLMClient
from settings import get_settings

ACADEMIC_MARKERS = (
    "acsi",
    "c-csi",
    "d&m",
    "delone",
    "mclean",
    "et al",
    "journal",
    "paper",
    "literature",
    "model",
    "satisfaction",
    "研究",
    "模型",
    "满意度",
    "文献",
    "综述",
    "论文",
    "期刊",
)

PRODUCT_MARKERS = (
    "official",
    "pricing",
    "plans",
    "features",
    "product",
    "app store",
    "google play",
    "review",
    "官网",
    "价格",
    "定价",
    "功能",
    "产品",
    "应用商店",
    "用户评价",
)


@dataclass(frozen=True)
class RelevanceResult:
    kept: list[SourceCitation]
    dropped: list[SourceCitation]


async def filter_relevant_sources(
    competitor_name: str,
    sources: list[SourceCitation],
    llm: LLMClient | None = None,
    *,
    include_raw_content: bool = False,
) -> RelevanceResult:
    if not sources:
        return RelevanceResult(kept=[], dropped=[])

    if llm is not None and llm.enabled:
        try:
            return await _filter_with_llm(
                competitor_name,
                sources,
                llm,
                include_raw_content=include_raw_content,
            )
        except Exception:
            pass

    kept: list[SourceCitation] = []
    dropped: list[SourceCitation] = []
    for source in sources:
        if _rule_says_irrelevant(source, include_raw_content=include_raw_content):
            dropped.append(source)
        else:
            kept.append(source)
    return RelevanceResult(kept=kept or sources, dropped=dropped if kept else [])


async def _filter_with_llm(
    competitor_name: str,
    sources: list[SourceCitation],
    llm: LLMClient,
    *,
    include_raw_content: bool,
) -> RelevanceResult:
    payload = await llm.complete_json(
        provider="openai",
        model=get_settings().collector_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Judge whether each source describes the named product, service, "
                    "or company itself: features, pricing, users, reviews, market, or "
                    "competition. Drop sources that only mention the name as a research "
                    "sample, satisfaction-model subject, literature review, or unrelated "
                    'concept. Return JSON {"decisions":[{"id":str,"keep":bool,'
                    '"reason":str}]} with one decision per source id.'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Competitor: {competitor_name}\n"
                    f"Sources: {[_source_payload(s, include_raw_content) for s in sources]}"
                ),
            },
        ],
    )
    decisions = {
        str(item.get("id")): bool(item.get("keep"))
        for item in payload.get("decisions", [])
        if isinstance(item, dict) and item.get("id")
    }
    if not decisions:
        raise ValueError("empty relevance decisions")

    kept = [source for source in sources if decisions.get(source.id, True)]
    dropped = [source for source in sources if not decisions.get(source.id, True)]
    return RelevanceResult(kept=kept or sources, dropped=dropped if kept else [])


def _source_payload(source: SourceCitation, include_raw_content: bool) -> dict[str, str]:
    text = source.raw_content or "" if include_raw_content else ""
    return {
        "id": source.id,
        "title": source.title,
        "snippet": source.snippet,
        "content_sample": text[:1000],
    }


def _rule_says_irrelevant(source: SourceCitation, *, include_raw_content: bool) -> bool:
    text = f"{source.title}\n{source.snippet}"
    if include_raw_content and source.raw_content:
        text = f"{text}\n{source.raw_content[:1500]}"
    lowered = text.lower()
    has_academic = any(marker in lowered for marker in ACADEMIC_MARKERS)
    has_product = any(marker in lowered for marker in PRODUCT_MARKERS)
    return has_academic and not has_product
