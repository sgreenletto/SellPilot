from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from sellpilot.core.enums import PromptStatus


class PromptVersionSummary(BaseModel):
    id: UUID
    version: int
    content: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    model_parameters: dict[str, Any]
    change_summary: str
    checksum: str
    created_at: datetime


class PromptTemplateSummary(BaseModel):
    id: UUID
    key: str
    name: str
    purpose: str
    task_type: str
    language: str
    status: str
    latest_version: PromptVersionSummary | None
    version_count: int
    created_at: datetime
    updated_at: datetime


class PromptVersionChangeRequest(BaseModel):
    content: str = Field(min_length=10, max_length=50_000)
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    model_parameters: dict[str, Any] = Field(default_factory=dict)
    change_summary: str = Field(min_length=3, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @field_validator("input_schema", "output_schema")
    @classmethod
    def validate_json_schema(cls, value: dict[str, Any]) -> dict[str, Any]:
        if value.get("type") != "object":
            raise ValueError("Prompt schemas must declare type=object")
        return value


class PromptStatusChangeRequest(BaseModel):
    status: PromptStatus
    idempotency_key: str = Field(min_length=8, max_length=128)


class ModelInvocationSummary(BaseModel):
    id: UUID
    provider: str
    model_name: str
    status: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: int
    retry_count: int
    estimated_cost: Decimal
    cost_currency: str
    error_code: str | None
    created_at: datetime


class ModelRuntimeSummary(BaseModel):
    provider: str
    model_name: str
    configured: bool
    base_url_configured: bool
    api_key_configured: bool
    timeout_seconds: float
    invocation_count: int
    success_count: int
    failure_count: int
    total_tokens: int
    estimated_cost: Decimal
    average_duration_ms: float


class EvaluationCaseSummary(BaseModel):
    case_id: str
    category: str
    passed: bool
    metrics: dict[str, Any] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)


class MemberThreeEvaluationSummary(BaseModel):
    dataset_version: str
    generated_at: datetime | None
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    cases: list[EvaluationCaseSummary]
    limitations: list[str]
