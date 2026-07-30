from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from sellpilot.schemas.confirmation import ConfirmationTaskResponse


class ImprovementGenerateRequest(BaseModel):
    analysis_id: UUID
    force_regenerate: bool = False


class ImprovementSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    suggestion_key: str
    category: str
    title: str
    description: str
    priority: int
    severity: Decimal
    confidence: Decimal
    evidence_count: int
    frequency_rate: Decimal
    evidence_review_ids: dict
    expected_impact: dict | None
    status: str


class ImprovementReportResponse(BaseModel):
    id: UUID
    review_analysis_result_id: UUID
    source_product_id: str
    version: int
    algorithm_version: str
    status: str
    source_type: str
    is_mock_data: bool
    data_sources: dict
    input_conditions: dict
    summary: dict
    created_at: datetime
    suggestions: list[ImprovementSuggestionResponse]


class SuggestionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    status: str | None = Field(default=None, pattern="^(PROPOSED|ACCEPTED|IGNORED)$")


class ImprovementDraftRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    site: str = Field(default="sg", min_length=2, max_length=16)
    target_language: Literal["und"] = "und"
    suggestion_ids: list[UUID] = Field(min_length=1, max_length=50)


class ImprovementDraftResponse(ConfirmationTaskResponse):
    pass


class ImprovementDraftItem(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=4000)


class ImprovementDraftVersionResponse(BaseModel):
    id: UUID
    content_id: UUID
    source_product_id: str
    site: str
    version: int
    sequence: int
    status: str
    report_id: UUID | None
    items: list[ImprovementDraftItem]
    change_summary: str
    created_at: datetime


class ImprovementDraftListResponse(BaseModel):
    items: list[ImprovementDraftVersionResponse]
    total: int


class ImprovementDraftRevisionRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    expected_version: int = Field(ge=1)
    items: list[ImprovementDraftItem] = Field(min_length=1, max_length=50)


class ImprovementDraftHistoryClearRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    source_product_id: str = Field(min_length=1, max_length=100)
