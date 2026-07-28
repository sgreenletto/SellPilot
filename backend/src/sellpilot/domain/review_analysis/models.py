from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sellpilot.core.enums import SiteCode
from sellpilot.schemas.common import SourceMetadata


class ReviewSentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class ReviewTopic(StrEnum):
    PRODUCT_QUALITY = "product_quality"
    PACKAGING = "packaging"
    DESCRIPTION_MISMATCH = "description_mismatch"
    LOGISTICS = "logistics"
    SERVICE = "service"
    MATERIAL = "material"
    SIZE_SPECIFICATION = "size_specification"
    WRONG_OR_MISSING_ITEM = "wrong_or_missing_item"
    OTHER = "other"
    NO_CLEAR_ISSUE = "no_clear_issue"


class TranslationStatus(StrEnum):
    NOT_NEEDED = "not_needed"
    PROVIDED = "provided"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class AnalysisOrigin(StrEnum):
    STATISTICAL_FACT = "statistical_fact"
    RULE = "rule"
    MODEL = "model"
    HUMAN = "human"


class QualityFlag(StrEnum):
    EMPTY = "empty"
    DUPLICATE = "duplicate"
    EMOJI_ONLY = "emoji_only"
    SPAM = "spam"
    TRUNCATED = "truncated"
    LANGUAGE_MISMATCH = "language_mismatch"
    UNKNOWN_LANGUAGE = "unknown_language"


class ReviewInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    review_id: str = Field(min_length=1, max_length=100)
    product_id: str = Field(min_length=1, max_length=100)
    site: SiteCode
    rating: int = Field(ge=1, le=5)
    content: str = Field(max_length=20000)
    translated_content: str | None = Field(default=None, max_length=20000)
    declared_language: str | None = Field(default=None, max_length=32)
    source_created_at: datetime
    source: SourceMetadata
    source_sentiment_hint: str | None = Field(default=None, max_length=32)
    source_issue_hint: str | None = Field(default=None, max_length=50)

    @field_validator("review_id", "product_id")
    @classmethod
    def strip_identifiers(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator(
        "translated_content",
        "declared_language",
        "source_sentiment_hint",
        "source_issue_hint",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ReviewAnalysisConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1, max_length=64)
    target_language: str = Field(default="zh-CN", min_length=2, max_length=32)
    maximum_content_length: int = Field(default=4000, ge=100, le=20000)
    model_timeout_seconds: Decimal = Field(default=Decimal("10"), gt=0, le=120)
    translation_timeout_seconds: Decimal = Field(default=Decimal("5"), gt=0, le=120)
    representative_limit: int = Field(default=3, ge=1, le=10)
    minimum_topic_confidence: Decimal = Field(default=Decimal("0.45"), ge=0, le=1)


class PreparedReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    review: ReviewInput
    normalized_content: str
    analysis_content: str
    display_translation: str | None
    detected_language: str
    translation_status: TranslationStatus
    quality_flags: tuple[QualityFlag, ...]
    included: bool
    duplicate_of: str | None = None


class ModelReviewLabel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str = Field(min_length=1, max_length=100)
    sentiment: ReviewSentiment
    topics: tuple[ReviewTopic, ...] = Field(min_length=1)
    confidence: Decimal = Field(ge=0, le=1)

    @field_validator("topics")
    @classmethod
    def unique_topics(cls, value: tuple[ReviewTopic, ...]) -> tuple[ReviewTopic, ...]:
        if len(value) != len(set(value)):
            raise ValueError("topics must be unique")
        return value


class ModelBatchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    labels: tuple[ModelReviewLabel, ...]


class ReviewModel(Protocol):
    async def analyze(self, reviews: tuple[PreparedReview, ...]) -> str | dict[str, object]: ...


class ReviewTranslator(Protocol):
    async def translate(
        self,
        text: str,
        *,
        source_language: str,
        target_language: str,
    ) -> str: ...


class ReviewJudgement(BaseModel):
    model_config = ConfigDict(frozen=True)

    review_id: str
    product_id: str
    site: SiteCode
    rating: int
    original_content: str
    translated_content: str | None
    display_content: str
    declared_language: str | None
    detected_language: str
    translation_status: TranslationStatus
    sentiment: ReviewSentiment
    topics: tuple[ReviewTopic, ...]
    confidence: Decimal = Field(ge=0, le=1)
    origin: AnalysisOrigin
    source_created_at: datetime
    quality_flags: tuple[QualityFlag, ...]


class EvidenceReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    review_id: str
    original_content: str
    translated_content: str | None
    language: str
    rating: int
    source_created_at: datetime
    sentiment: ReviewSentiment
    confidence: Decimal = Field(ge=0, le=1)


class TopicAggregate(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic: ReviewTopic
    count: int = Field(ge=0)
    frequency_rate: Decimal = Field(ge=0, le=1)
    negative_count: int = Field(ge=0)
    severity: Decimal = Field(ge=0, le=1)
    evidence: tuple[EvidenceReference, ...]


class PainPointAggregate(BaseModel):
    model_config = ConfigDict(frozen=True)

    pain_point: ReviewTopic
    negative_count: int = Field(gt=0)
    frequency_rate: Decimal = Field(gt=0, le=1)
    severity: Decimal = Field(gt=0, le=1)
    affected_sites: tuple[SiteCode, ...]
    evidence: tuple[EvidenceReference, ...] = Field(min_length=1)


class KeywordAggregate(BaseModel):
    model_config = ConfigDict(frozen=True)

    keyword: str = Field(min_length=1, max_length=100)
    count: int = Field(gt=0)
    review_count: int = Field(gt=0)
    review_ids: tuple[str, ...] = Field(min_length=1)


class SentimentAggregate(BaseModel):
    model_config = ConfigDict(frozen=True)

    positive: int = Field(ge=0)
    neutral: int = Field(ge=0)
    negative: int = Field(ge=0)


class TrendPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    site: SiteCode
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    review_count: int = Field(ge=0)
    negative_count: int = Field(ge=0)
    average_rating: Decimal = Field(ge=1, le=5)
    topic_counts: dict[ReviewTopic, int]


class QualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    received_count: int = Field(ge=0)
    included_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    flag_counts: dict[QualityFlag, int]
    excluded_review_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_totals(self) -> "QualityReport":
        if self.included_count + self.excluded_count != self.received_count:
            raise ValueError("quality counts must reconcile")
        return self


class ReviewAnalysisReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    analyzer_version: str
    product_ids: tuple[str, ...]
    source: SourceMetadata
    is_mock_data: bool
    quality: QualityReport
    sentiment: SentimentAggregate
    topics: tuple[TopicAggregate, ...]
    pain_points: tuple[PainPointAggregate, ...]
    keywords: tuple[KeywordAggregate, ...]
    trends: tuple[TrendPoint, ...]
    judgements: tuple[ReviewJudgement, ...]
    facts: tuple[str, ...]

    @model_validator(mode="after")
    def validate_evidence_and_aggregates(self) -> "ReviewAnalysisReport":
        known_ids = {item.review_id for item in self.judgements}
        for aggregate in self.topics:
            if aggregate.count and not aggregate.evidence:
                raise ValueError(f"topic {aggregate.topic} must include evidence")
            if any(item.review_id not in known_ids for item in aggregate.evidence):
                raise ValueError("topic evidence must reference an input judgement")
        for pain_point in self.pain_points:
            if any(item.review_id not in known_ids for item in pain_point.evidence):
                raise ValueError("pain-point evidence must reference an input judgement")
        for keyword in self.keywords:
            if any(review_id not in known_ids for review_id in keyword.review_ids):
                raise ValueError("keyword references must point to input judgements")
        if self.sentiment.positive + self.sentiment.neutral + self.sentiment.negative != len(
            self.judgements
        ):
            raise ValueError("sentiment counts must reconcile with judgements")
        return self
