from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    model_validator,
)

from sellpilot.core.enums import ToolCallerType, ToolCallStatus, ToolRiskLevel
from sellpilot.schemas.common import ApiDateTime, IdempotencyKey
from sellpilot.tools.sanitization import audit_summary

if TYPE_CHECKING:
    from sellpilot.db.models.tool_call import ToolCall

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

    @model_validator(mode="before")
    @classmethod
    def sanitize_public_response(cls, value: Any) -> Any:
        if hasattr(value, "input_summary") and hasattr(value, "attempt_history"):
            return cls._safe_data(value, max_bytes=16_384)
        return value

    @classmethod
    def from_tool_call(
        cls,
        tool_call: "ToolCall",
        *,
        max_bytes: int,
    ) -> "ToolCallResponse":
        return cls.model_validate(cls._safe_data(tool_call, max_bytes=max_bytes))

    @staticmethod
    def _safe_data(
        tool_call: "ToolCall",
        *,
        max_bytes: int,
    ) -> dict[str, object]:
        def safe_summary(value: object | None) -> dict[str, JsonValue] | None:
            if value is None:
                return None
            return audit_summary(value, max_bytes=max_bytes)

        return {
            "id": tool_call.id,
            "tool_name": tool_call.tool_name,
            "tool_version": tool_call.tool_version,
            "risk_level": ToolRiskLevel(tool_call.risk_level),
            "caller_type": ToolCallerType(tool_call.caller_type),
            "caller_name": tool_call.caller_name,
            "request_id": tool_call.request_id,
            "user_id": tool_call.user_id,
            "task_id": tool_call.task_id,
            "task_step_id": tool_call.task_step_id,
            "confirmation_id": tool_call.confirmation_id,
            "input_summary": safe_summary(tool_call.input_summary),
            "output_summary": safe_summary(tool_call.output_summary),
            "attempt_history": safe_summary(tool_call.attempt_history),
            "status": ToolCallStatus(tool_call.status),
            "attempt_count": tool_call.attempt_count,
            "duration_ms": tool_call.duration_ms,
            "error_code": tool_call.error_code,
            "error_message": tool_call.error_message,
            "started_at": tool_call.started_at,
            "completed_at": tool_call.completed_at,
            "created_at": tool_call.created_at,
        }


class ToolCallFilters(BaseModel):
    tool_name: str | None = Field(default=None, min_length=1, max_length=100)
    status: ToolCallStatus | None = None
    risk_level: ToolRiskLevel | None = None
    task_id: UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
