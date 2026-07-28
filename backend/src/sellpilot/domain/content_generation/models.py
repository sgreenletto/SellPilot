from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListingFacts(StrictModel):
    product_id: str
    title: str
    description: str
    category_name: str
    site: str
    target_language: str
    audience: str = "general"
    selling_points: list[str] = Field(default_factory=list)
    requested_keywords: list[str] = Field(default_factory=list)
    specifications: dict[str, str] = Field(default_factory=dict)
    sku_facts: list[dict[str, Any]] = Field(default_factory=list)


class FaqItem(StrictModel):
    question: str = Field(min_length=1, max_length=300)
    answer: str = Field(min_length=1, max_length=1000)


class SkuContentItem(StrictModel):
    sku: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)


class LocalizedListing(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    bullet_points: list[str] = Field(min_length=3, max_length=8)
    description: str = Field(min_length=1, max_length=5000)
    marketing_copy: str = Field(min_length=1, max_length=1000)
    faq: list[FaqItem] = Field(default_factory=list, max_length=10)
    sku_content: list[SkuContentItem] = Field(default_factory=list)
    keywords: list[str] = Field(min_length=1, max_length=30)
    target_language: str
    generation_mode: str


class QualityResult(StrictModel):
    passed: bool
    title_length: int
    keyword_coverage: float
    fact_issues: list[str]
    compliance_issues: list[str]
    completeness_issues: list[str]
    attempts: int


class GeneratedListing(StrictModel):
    content: LocalizedListing
    quality: QualityResult


class ModelGateway(Protocol):
    provider: str
    model_name: str
    generation_mode: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    async def generate(
        self, facts: ListingFacts, issues: list[str] | None = None
    ) -> LocalizedListing: ...
