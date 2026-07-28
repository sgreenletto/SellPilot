from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from sellpilot.core.enums import AnalysisStatus, SiteCode, TaskStepStatus
from sellpilot.domain.review_analysis.models import (
    KeywordAggregate,
    PainPointAggregate,
    QualityReport,
    ReviewJudgement,
    SentimentAggregate,
    TopicAggregate,
    TrendPoint,
)
from sellpilot.schemas.common import ContractModel, IdempotencyKey

ReviewAnalysisMode = Literal["rule", "validated_model"]


class ReviewQuery(ContractModel):
    product_id: str = Field(min_length=1, max_length=100)
    site: SiteCode | None = None
    language: str | None = Field(default=None, min_length=2, max_length=32)
    min_rating: int | None = Field(default=None, ge=1, le=5)
    max_rating: int | None = Field(default=None, ge=1, le=5)
    created_from: datetime | None = None
    created_to: datetime | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_ranges(self) -> "ReviewQuery":
        if (
            self.min_rating is not None
            and self.max_rating is not None
            and self.min_rating > self.max_rating
        ):
            raise ValueError("min_rating must not exceed max_rating")
        if (
            self.created_from is not None
            and self.created_to is not None
            and self.created_from > self.created_to
        ):
            raise ValueError("created_from must not exceed created_to")
        return self


class ReviewResponse(ContractModel):
    review_id: str
    product_id: str
    site: SiteCode
    rating: int
    content: str
    translated_content: str | None
    language: str
    sentiment_hint: str
    issue_type: str
    created_at: datetime
    source_type: str
    is_mock_data: bool


class ReviewAnalysisCreateRequest(ContractModel):
    idempotency_key: IdempotencyKey
    product_id: str = Field(min_length=1, max_length=100)
    site: SiteCode | None = None
    languages: list[str] = Field(default_factory=list, max_length=10)
    min_rating: int | None = Field(default=None, ge=1, le=5)
    max_rating: int | None = Field(default=None, ge=1, le=5)
    created_from: datetime | None = None
    created_to: datetime | None = None
    batch_size: int = Field(default=100, ge=1, le=100)
    maximum_reviews: int = Field(default=1000, ge=1, le=5000)
    max_attempts: int = Field(default=2, ge=1, le=3)

    @model_validator(mode="after")
    def validate_ranges_and_languages(self) -> "ReviewAnalysisCreateRequest":
        ReviewQuery(
            product_id=self.product_id,
            site=self.site,
            min_rating=self.min_rating,
            max_rating=self.max_rating,
            created_from=self.created_from,
            created_to=self.created_to,
        )
        normalized = [item.strip() for item in self.languages]
        if any(not item or len(item) > 32 for item in normalized):
            raise ValueError("languages must contain non-blank values up to 32 characters")
        if len(normalized) != len(set(normalized)):
            raise ValueError("languages must be unique")
        self.languages[:] = normalized
        return self


class ReviewAnalysisCreatedResponse(ContractModel):
    analysis_id: UUID
    agent_task_id: UUID
    status: AnalysisStatus
    duplicate: bool
    analyzer_version: str
    analysis_mode: ReviewAnalysisMode
    prompt_version: str | None
    model_version: str | None
    is_mock_data: bool


class ReviewTaskStepResponse(ContractModel):
    step_name: str
    status: TaskStepStatus
    input_summary: dict[str, object] | None
    output_summary: dict[str, object] | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None


class ReviewAnalysisResultResponse(ContractModel):
    analysis_id: UUID
    agent_task_id: UUID | None
    product_id: str
    site: SiteCode
    status: AnalysisStatus
    progress: int = Field(ge=0, le=100)
    current_step: str | None
    steps: tuple[ReviewTaskStepResponse, ...]
    analyzer_version: str
    analysis_mode: ReviewAnalysisMode
    prompt_version: str | None
    model_version: str | None
    quality: QualityReport | None
    sentiment: SentimentAggregate | None
    topics: tuple[TopicAggregate, ...]
    pain_points: tuple[PainPointAggregate, ...]
    keywords: tuple[KeywordAggregate, ...]
    trends: tuple[TrendPoint, ...]
    judgements: tuple[ReviewJudgement, ...]
    error_message: str | None
    is_mock_data: bool
    started_at: datetime | None
    finished_at: datetime | None


class ReviewEvidenceResponse(ContractModel):
    id: UUID
    review_id: str
    product_id: str
    language: str
    rating: int
    evidence_type: str
    label: str
    sentiment: str | None
    issue_type: str | None
    original_content: str
    translated_content: str | None
    source_created_at: datetime
    confidence: Decimal
    metadata: dict[str, object] | None
    is_mock_data: bool


class ReviewEvidencePage(ContractModel):
    items: list[ReviewEvidenceResponse]
    page: int
    page_size: int
    total: int
