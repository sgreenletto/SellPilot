from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from sellpilot.domain.content_generation.models import GeneratedListing
from sellpilot.schemas.confirmation import ConfirmationTaskResponse


class ContentGenerateRequest(BaseModel):
    product_id: str = Field(min_length=1, max_length=100)
    site: Literal["sg", "my", "ph", "th", "vn", "id", "tw", "br"] = "sg"
    target_language: Literal["zh-CN", "en", "ms", "id", "th", "vi", "tl", "pt-BR", "zh-TW"]
    audience: str = Field(default="general", min_length=1, max_length=200)
    selling_points: list[str] = Field(default_factory=list, max_length=8)
    keywords: list[str] = Field(default_factory=list, max_length=30)
    max_attempts: int = Field(default=3, ge=1, le=3)


class ContentGenerateResponse(BaseModel):
    task_id: UUID
    product_id: str
    site: str
    target_language: str
    audience: str
    selling_points: list[str]
    keywords: list[str]
    result: GeneratedListing
    provider: str
    model_name: str
    invocation_id: UUID


class ContentDraftRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    generation: ContentGenerateResponse


class ContentRestoreRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    version_id: UUID


class ContentVersionResponse(BaseModel):
    id: UUID
    content_id: UUID
    version: int
    title: str
    bullet_points: dict[str, Any]
    description: str
    marketing_copy: str
    faq: dict[str, Any] | None
    sku_content: dict[str, Any] | None
    keywords: dict[str, Any] | None
    fact_check_result: dict[str, Any]
    compliance_result: dict[str, Any]
    change_type: str
    change_summary: str
    created_at: datetime


class ContentVersionsResponse(BaseModel):
    content_id: UUID
    items: list[ContentVersionResponse]
    total: int


class ContentDraftConfirmationResponse(ConfirmationTaskResponse):
    pass
