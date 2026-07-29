import re
import unicodedata
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from sellpilot.domain.content_generation.models import (
    GeneratedListing,
    ListingFacts,
    LocalizedListing,
    ModelGateway,
    QualityResult,
)

FORBIDDEN = (
    "best ever",
    "guaranteed",
    "100% cure",
    "no.1",
    "number one",
    "永久第一",
    "绝对保证",
    "全网最低",
    "百分百有效",
    "零风险",
)
SITE_TITLE_LIMITS = {
    "sg": 120,
    "my": 120,
    "ph": 120,
    "th": 120,
    "vn": 120,
    "id": 120,
    "tw": 120,
    "br": 120,
}
UNSUPPORTED_CLAIM_MARKERS = (
    "实测",
    "无需驱动",
    "即插即用",
    "同时稳定",
    "兼容windows",
    "兼容macos",
    "兼容android",
)
TECHNICAL_TOKEN_PATTERN = re.compile(
    r"(?<![a-z0-9])(?:usb(?:-[ac])?|hdmi|micro\s*sd|sd|pd)(?![a-z0-9])"
    r"|(?<![a-z0-9])\d+(?:\.\d+)?(?:k|p|hz|w|gbps)(?![a-z0-9])",
    re.IGNORECASE,
)
FACTUAL_KEYWORD_MARKERS = (
    "容量",
    "功率",
    "瓦",
    "尺寸",
    "材质",
    "认证",
    "保修",
    "防水",
    "续航",
    "capacity",
    "watt",
    "material",
    "certified",
    "warranty",
    "waterproof",
    "battery life",
)


def _normalized(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = re.sub(r"(\d+)\s*(?:-|–|—)?\s*in\s*(?:-|–|—)?\s*1", r"\1合1", normalized)
    return re.sub(r"[\W_]+", "", normalized)


def _keyword_occurrences(text: str, keyword: str) -> int:
    """Count natural keyword occurrences without matching technical tokens as substrings."""
    normalized_keyword = unicodedata.normalize("NFKC", keyword).casefold().strip()
    if not normalized_keyword:
        return 0
    if re.fullmatch(r"[a-z0-9][a-z0-9+\-.\s]*", normalized_keyword):
        pattern = rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])"
        return len(re.findall(pattern, unicodedata.normalize("NFKC", text).casefold()))
    return _normalized(text).count(_normalized(normalized_keyword))


def _localized_fact_variants(value: str) -> set[str]:
    variants = {_normalized(value)}
    match = re.fullmatch(r"\s*(\d+)\s*(?:-|–|—)?\s*in\s*(?:-|–|—)?\s*1\s*", value, re.I)
    if match:
        variants.add(_normalized(f"{match.group(1)}合1"))
    return variants


def _source_text(facts: ListingFacts) -> str:
    sku_values = [
        str(value) for item in facts.sku_facts for value in item.values() if value is not None
    ]
    return " ".join(
        [
            facts.title,
            facts.description,
            facts.category_name,
            *facts.specifications.keys(),
            *facts.specifications.values(),
            *sku_values,
        ]
    )


def _is_language_neutral_keyword(value: str) -> bool:
    compact = re.sub(r"[\s/_-]+", "", value).lower()
    return bool(
        compact
        and re.fullmatch(
            r"(?:usb[ac]?|hdmi|pd|sd|microsd|\d+(?:in1|合1|k|p|hz|w|gbps)?)",
            compact,
        )
    )


def check_listing(content: LocalizedListing, facts: ListingFacts, attempts: int) -> QualityResult:
    text = " ".join(
        [
            content.title,
            *content.bullet_points,
            content.description,
            content.marketing_copy,
            *(item.question for item in content.faq),
            *(item.answer for item in content.faq),
            *(item.description for item in content.sku_content),
        ]
    ).lower()
    normalized_text = _normalized(text)
    source_text = _source_text(facts)
    normalized_source = _normalized(source_text)
    fact_issues: list[str] = []
    protected_values = [value for value in facts.specifications.values() if value]
    for value in protected_values:
        if not any(variant in normalized_text for variant in _localized_fact_variants(value)):
            fact_issues.append(f"missing protected fact: {value}")
    unsupported_markers = [
        marker
        for marker in UNSUPPORTED_CLAIM_MARKERS
        if _normalized(marker) in normalized_text and _normalized(marker) not in normalized_source
    ]
    fact_issues.extend(f"unsupported claim: {marker}" for marker in unsupported_markers)
    unsupported_tokens = sorted(
        {
            match.group(0)
            for match in TECHNICAL_TOKEN_PATTERN.finditer(text)
            if _normalized(match.group(0)) not in normalized_source
        }
    )
    fact_issues.extend(f"unsupported technical fact: {token}" for token in unsupported_tokens)
    compliance = [
        f"forbidden claim: {term}" for term in FORBIDDEN if _normalized(term) in normalized_text
    ]
    seo_issues: list[str] = []
    localization_issues: list[str] = []
    completeness = []
    if content.target_language != facts.target_language:
        completeness.append("target language does not match the request")
    site_limit = SITE_TITLE_LIMITS.get(facts.site.lower(), 120)
    if len(content.title) > site_limit:
        compliance.append(f"title exceeds site limit: {site_limit}")
    if len(content.bullet_points) < 3:
        completeness.append("at least three bullet points are required")
    expected_skus = {
        str(item.get("seller_sku") or item.get("sku") or "")
        for item in facts.sku_facts
        if item.get("seller_sku") or item.get("sku")
    }
    actual_skus = {item.sku for item in content.sku_content}
    missing_skus = sorted(expected_skus - actual_skus)
    completeness.extend(f"missing SKU content: {sku}" for sku in missing_skus)
    keywords = [item.strip() for item in facts.requested_keywords if item.strip()]
    unsupported_keywords = [
        item
        for item in keywords
        if any(_normalized(marker) in _normalized(item) for marker in FACTUAL_KEYWORD_MARKERS)
        and _normalized(item) not in normalized_source
    ]
    eligible_keywords = [item for item in keywords if item not in unsupported_keywords]
    seo_issues.extend(f"unsupported factual keyword: {item}" for item in unsupported_keywords)
    if facts.target_language in {"zh-CN", "zh-TW"}:
        requested_keyword_text = normalized_text
    elif content.keyword_suggestions_zh:
        requested_keyword_text = _normalized(" ".join(content.keyword_suggestions_zh))
    elif all(not re.search(r"[\u3400-\u9fff]", item) for item in eligible_keywords):
        requested_keyword_text = normalized_text
    else:
        requested_keyword_text = ""
    missing_keywords = [
        item for item in eligible_keywords if _normalized(item) not in requested_keyword_text
    ]
    coverage = (
        (len(eligible_keywords) - len(missing_keywords)) / len(eligible_keywords)
        if eligible_keywords
        else 1.0
    )
    seo_issues.extend(f"missing requested keyword: {item}" for item in missing_keywords)
    normalized_generated = [_normalized(item) for item in content.keywords if _normalized(item)]
    if len(normalized_generated) != len(set(normalized_generated)):
        seo_issues.append("duplicate generated keywords")
    title_candidates = (
        eligible_keywords if facts.target_language in {"zh-CN", "zh-TW"} else content.keywords
    )
    if title_candidates and not any(
        _normalized(item) in _normalized(content.title) for item in title_candidates
    ):
        seo_issues.append("title does not contain a target-market keyword")
    stuffing_candidates = [
        *content.keywords,
        *(eligible_keywords if facts.target_language in {"zh-CN", "zh-TW"} else []),
    ]
    promotional_text = " ".join(
        [
            content.title,
            *content.bullet_points,
            content.description,
            content.marketing_copy,
        ]
    )
    for keyword in set(stuffing_candidates):
        if _keyword_occurrences(promotional_text, keyword) > 5:
            seo_issues.append(f"keyword stuffing: {keyword}")
    natural_text = " ".join([*content.bullet_points, content.description, content.marketing_copy])
    if facts.target_language in {"zh-CN", "zh-TW"} and not re.search(
        r"[\u3400-\u9fff]", natural_text
    ):
        localization_issues.append("content is not localized to Chinese")
    if facts.target_language == "th" and not re.search(r"[\u0e00-\u0e7f]", natural_text):
        localization_issues.append("content is not localized to Thai")
    if facts.target_language in {"zh-CN", "zh-TW"}:
        localization_issues.extend(
            f"keyword not localized: {item}"
            for item in content.keywords
            if not re.search(r"[\u3400-\u9fff]", item) and not _is_language_neutral_keyword(item)
        )
    return QualityResult(
        passed=not any([fact_issues, compliance, seo_issues, localization_issues, completeness]),
        title_length=len(content.title),
        keyword_coverage=round(coverage, 4),
        fact_issues=fact_issues,
        compliance_issues=compliance,
        seo_issues=seo_issues,
        localization_issues=localization_issues,
        completeness_issues=completeness,
        attempts=attempts,
    )


async def generate_with_quality_loop(
    gateway: ModelGateway, facts: ListingFacts, max_attempts: int = 3
) -> GeneratedListing:
    class ContentQualityState(TypedDict):
        attempt: int
        issues: list[str]
        content: Any
        quality: Any

    async def generate(state: ContentQualityState) -> dict[str, Any]:
        content = await gateway.generate(facts, state["issues"])
        return {"attempt": state["attempt"] + 1, "content": content}

    async def validate(state: ContentQualityState) -> dict[str, Any]:
        quality = check_listing(state["content"], facts, state["attempt"])
        return {
            "quality": quality,
            "issues": [
                *quality.fact_issues,
                *quality.compliance_issues,
                *quality.seo_issues,
                *quality.localization_issues,
                *quality.completeness_issues,
            ],
        }

    def route(state: ContentQualityState) -> Literal["generate", "__end__"]:
        if any(
            issue.startswith("unsupported factual keyword:")
            for issue in state["quality"].seo_issues
        ):
            return END
        if state["quality"].passed or state["attempt"] >= max_attempts:
            return END
        return "generate"

    graph = StateGraph(ContentQualityState)
    graph.add_node("generate", generate)
    graph.add_node("validate", validate)
    graph.add_edge(START, "generate")
    graph.add_edge("generate", "validate")
    graph.add_conditional_edges("validate", route, {"generate": "generate", END: END})
    workflow = graph.compile(name="sellpilot_content_quality_loop")
    final = await workflow.ainvoke({"attempt": 0, "issues": [], "content": None, "quality": None})
    return GeneratedListing(content=final["content"], quality=final["quality"])
