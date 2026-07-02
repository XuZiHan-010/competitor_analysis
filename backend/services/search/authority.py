import contextlib
from urllib.parse import urlparse

from schemas.source import SourceCategory, SourceCitation
from services.llm import LLMClient, provider_for_model
from settings import get_settings

# A (official / authoritative) > B (credible secondary media) > C (UGC / blogs / unknown).
_TIER_ORDER = {"A": 0, "B": 1, "C": 2}

# Domains whose TLD alone signals a high-authority publisher → tier A.
_AUTHORITATIVE_TLDS = (".gov", ".gov.cn", ".edu", ".edu.cn", ".int", ".mil", ".ac.uk")

# Host substrings signalling low-authority UGC / blogs / social / forums → tier C.
_UGC_HOST_MARKERS = (
    "reddit.",
    "quora.",
    "medium.com",
    "blogspot.",
    "wordpress.",
    "substack.",
    "zhihu.",
    "tieba.",
    "weibo.",
    "csdn.",
    "jianshu.",
    "facebook.",
    "twitter.",
    "x.com",
    "youtube.",
    "tiktok.",
    "wikipedia.",
)

_UGC_SOURCE_TYPES = {
    "app_review",
    "public_review",
    "user_feedback",
    "user_uploaded",
    "ai_simulated",
}


async def grade_source_authority(
    competitor_name: str,
    sources: list[SourceCitation],
    llm: LLMClient | None = None,
    *,
    include_raw_content: bool = False,
) -> list[SourceCitation]:
    """Grade each source into authority tier A/B/C and return sorted A→B→C.

    Cheap deterministic rules decide the strong signals (official domain, government
    /academic TLDs, obvious UGC); everything else is graded by one batched LLM call.
    On any LLM failure ungraded sources fall back to C — we never over-claim A.
    """
    if not sources:
        return []

    tiers: dict[str, str] = {}
    ungraded: list[SourceCitation] = []
    for source in sources:
        rule_tier = _rule_tier(source, competitor_name)
        if rule_tier is not None:
            tiers[source.id] = rule_tier
        else:
            ungraded.append(source)

    if ungraded and llm is not None and llm.enabled:
        with contextlib.suppress(Exception):
            tiers.update(
                await _grade_with_llm(
                    competitor_name,
                    ungraded,
                    llm,
                    include_raw_content=include_raw_content,
                )
            )

    graded: list[SourceCitation] = []
    for source in sources:
        update: dict[str, object] = {"tier": tiers.get(source.id, "C")}
        # Providers stamp every web result "media"; upgrade the product's own official
        # domain to category "official" so the pricing gate (which keys on
        # type/category, not tier) stops treating an official pricing page as a weak
        # source. Only touch the still-generic media/unknown labels — never override a
        # deliberate UGC/commercial classification.
        origin = classify_source_origin(source, competitor_name)
        if origin is not None and source.category in ("media", "unknown"):
            update["category"] = origin
        graded.append(source.model_copy(update=update))
    # Stable sort keeps the original within-tier ordering (relevance/recency signal).
    graded.sort(key=lambda source: _TIER_ORDER.get(source.tier or "C", 2))
    return graded


async def _grade_with_llm(
    competitor_name: str,
    sources: list[SourceCitation],
    llm: LLMClient,
    *,
    include_raw_content: bool,
) -> dict[str, str]:
    payload = await llm.complete_json(
        provider=provider_for_model(get_settings().collector_model),
        model=get_settings().collector_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Grade each source's authority for competitive analysis of the named "
                    "product/company into tier A, B, or C. "
                    "A = the product's own official site / docs / pricing / press release, or a "
                    "government, industry-association, or well-known research institution / "
                    "authoritative official outlet. "
                    "B = credible secondary reporting with editorial oversight (mainstream or "
                    "well-known industry media). "
                    "C = user reviews, personal blogs, forums, UGC, or unknown / low-credibility "
                    "outlets. When unsure, prefer the lower tier. "
                    'Return JSON {"grades":[{"id":str,"tier":"A|B|C","reason":str}]} '
                    "with one entry per source id."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Product/company: {competitor_name}\n"
                    "Sources: "
                    f"{[_source_payload(source, include_raw_content) for source in sources]}"
                ),
            },
        ],
    )
    grades: dict[str, str] = {}
    for item in payload.get("grades", []):
        if not isinstance(item, dict):
            continue
        source_id = item.get("id")
        tier = item.get("tier")
        if source_id and tier in _TIER_ORDER:
            grades[str(source_id)] = str(tier)
    return grades


def classify_source_origin(
    source: SourceCitation, competitor_name: str
) -> SourceCategory | None:
    """Origin category implied by the source host, or None when the host is inconclusive.

    Returns "official" for the product's own domain or a government/academic publisher.
    Shared by ``_rule_tier`` (tier A) and the collector's category re-stamp so the domain
    rules can't drift apart.
    """
    host = _host(source)
    if not host:
        return None
    if _host_is_official(host, competitor_name):
        return "official"
    if any(host.endswith(tld) for tld in _AUTHORITATIVE_TLDS):
        return "official"
    return None


def _rule_tier(source: SourceCitation, competitor_name: str) -> str | None:
    if source.type in _UGC_SOURCE_TYPES:
        return "C"
    if classify_source_origin(source, competitor_name) == "official":
        return "A"
    host = _host(source)
    if host and any(marker in host for marker in _UGC_HOST_MARKERS):
        return "C"
    return None


def _host_is_official(host: str, competitor_name: str) -> bool:
    """A brand token appearing as an exact host label implies the product's own domain.

    Exact-label match (not substring) avoids false positives like ``notionfans.com``
    grading as A for competitor "Notion".
    """
    labels = set(host.split("."))
    return any(token in labels for token in _brand_tokens(competitor_name))


def _brand_tokens(competitor_name: str) -> list[str]:
    return [
        token
        for raw in competitor_name.lower().split()
        if len(token := "".join(ch for ch in raw if ch.isalnum())) >= 3
    ]


def _host(source: SourceCitation) -> str:
    if not source.url:
        return ""
    return (urlparse(str(source.url)).hostname or "").lower()


def _source_payload(source: SourceCitation, include_raw_content: bool) -> dict[str, str]:
    return {
        "id": source.id,
        "url": str(source.url) if source.url else "",
        "title": source.title,
        "snippet": source.snippet,
        "content_sample": (source.raw_content or "")[:800] if include_raw_content else "",
    }
