from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints

from sellpilot.core.enums import ToolCallerType, ToolCallStatus, ToolRiskLevel
from sellpilot.schemas.common import ApiDateTime, IdempotencyKey

TargetType = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_.-]*$",
    ),
]


class ToolExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: dict[str, JsonValue] = Field(default_factory=dict)
    task_id: UUID | None = None
    task_step_id: UUID | None = None
    idempotency_key: IdempotencyKey | None = None
    target_type: TargetType = "tool"
    target_id: str | None = Field(default=None, max_length=255)
    before_snapshot: dict[str, JsonValue] | None = None
    after_snapshot: dict[str, JsonValue] | None = None
    risk_warning: str | None = Field(default=None, min_length=1, max_length=1000)


class ToolCallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tool_name: str
    tool_version: str
    risk_level: ToolRiskLevel
    caller_type: ToolCallerType
    caller_name: str | None
    request_id: str
    user_id: UUID | None
    task_id: UUID | None
    task_step_id: UUID | None
    confirmation_id: UUID | None
    input_summary: dict[str, JsonValue] | None
    output_summary: dict[str, JsonValue] | None
    attempt_history: dict[str, JsonValue] | None
    status: ToolCallStatus
    attempt_count: int
    duration_ms: int | None
    error_code: str | None
    error_message: str | None
    started_at: ApiDateTime
    completed_at: ApiDateTime | None
    created_at: ApiDateTime


class ToolCallFilters(BaseModel):
    tool_name: str | None = Field(default=None, min_length=1, max_length=100)
    status: ToolCallStatus | None = None
    risk_level: ToolRiskLevel | None = None
    task_id: UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
