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

FORBIDDEN = ("best ever", "guaranteed", "100% cure", "永久第一", "绝对保证")
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


def _normalized(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = re.sub(r"(\d+)\s*(?:-|–|—)?\s*in\s*(?:-|–|—)?\s*1", r"\1合1", normalized)
    return re.sub(r"[\W_]+", "", normalized)


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
    compliance = [f"forbidden claim: {term}" for term in FORBIDDEN if term in text]
    completeness = []
    if content.target_language != facts.target_language:
        completeness.append("target language does not match the request")
    if len(content.title) > 200:
        completeness.append("title exceeds 200 characters")
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
    missing_keywords = [item for item in keywords if _normalized(item) not in normalized_text]
    coverage = (len(keywords) - len(missing_keywords)) / max(len(keywords), 1)
    completeness.extend(f"missing requested keyword: {item}" for item in missing_keywords)
    return QualityResult(
        passed=not fact_issues and not compliance and not completeness,
        title_length=len(content.title),
        keyword_coverage=round(coverage, 4),
        fact_issues=fact_issues,
        compliance_issues=compliance,
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
                *quality.completeness_issues,
            ],
        }

    def route(state: ContentQualityState) -> Literal["generate", "__end__"]:
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
