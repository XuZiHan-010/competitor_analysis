from dataclasses import dataclass

from schemas.source import SourceCitation
from services.llm import LLMClient, provider_for_model
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
    "satisfaction",
    "研究",
    "满意度",
    "文献",
    "综述",
    "论文",
    "期刊",
)

ACADEMIC_MODEL_PHRASES = (
    "satisfaction model",
    "acsi model",
    "c-csi model",
    "delone model",
    "mclean model",
    "literature model",
    "research model",
    "研究模型",
    "满意度模型",
    "模型研究",
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

HARD_FACT_DIMENSIONS = frozenset({
    "core.feature_tree",
    "core.pricing",
    "core.swot",
})


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
            kept.append(_tag_academic_sample(source, include_raw_content=include_raw_content))
    return RelevanceResult(kept=kept, dropped=dropped)


async def _filter_with_llm(
    competitor_name: str,
    sources: list[SourceCitation],
    llm: LLMClient,
    *,
    include_raw_content: bool,
) -> RelevanceResult:
    payload = await llm.complete_json(
        provider=provider_for_model(get_settings().collector_model),
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

    kept = [
        _tag_academic_sample(source, include_raw_content=include_raw_content)
        for source in sources
        if decisions.get(source.id, True)
    ]
    dropped = [source for source in sources if not decisions.get(source.id, True)]
    return RelevanceResult(kept=kept, dropped=dropped)


def _source_payload(source: SourceCitation, include_raw_content: bool) -> dict[str, str]:
    text = source.raw_content or "" if include_raw_content else ""
    return {
        "id": source.id,
        "title": source.title,
        "snippet": source.snippet,
        "content_sample": text[:1000],
    }


def _rule_says_irrelevant(source: SourceCitation, *, include_raw_content: bool) -> bool:
    lowered = _source_text(source, include_raw_content=include_raw_content).lower()
    has_academic = _has_academic_context(lowered)
    has_product = any(marker in lowered for marker in PRODUCT_MARKERS)
    if not has_academic:
        return False
    if source.dimension_id in HARD_FACT_DIMENSIONS:
        return not has_product
    return not has_product


def _tag_academic_sample(
    source: SourceCitation,
    *,
    include_raw_content: bool,
) -> SourceCitation:
    lowered = _source_text(source, include_raw_content=include_raw_content).lower()
    has_academic = _has_academic_context(lowered)
    has_product = any(marker in lowered for marker in PRODUCT_MARKERS)
    if has_academic and not has_product:
        return source.model_copy(update={"category": "academic_sample"})
    return source


def _has_academic_context(text: str) -> bool:
    return any(marker in text for marker in ACADEMIC_MARKERS) or any(
        phrase in text for phrase in ACADEMIC_MODEL_PHRASES
    )


def _source_text(source: SourceCitation, *, include_raw_content: bool) -> str:
    text = f"{source.title}\n{source.snippet}"
    if include_raw_content and source.raw_content:
        text = f"{text}\n{source.raw_content[:1500]}"
    return text
