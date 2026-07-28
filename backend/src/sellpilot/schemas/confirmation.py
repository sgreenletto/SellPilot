from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

from sellpilot.core.enums import ConfirmationStatus, ToolRiskLevel
from sellpilot.core.logging import redact_sensitive
from sellpilot.schemas.common import ApiDateTime
from sellpilot.tools.sanitization import audit_summary

if TYPE_CHECKING:
    from sellpilot.db.models.confirmation_task import ConfirmationTask


class ConfirmationTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_task_id: UUID
    task_step_id: UUID | None
    operation_type: str
    target_type: str
    target_id: str | None
    risk_level: ToolRiskLevel
    before_snapshot: dict[str, JsonValue] | None
    after_snapshot: dict[str, JsonValue] | None
    status: ConfirmationStatus
    idempotency_key: str
    created_by: UUID
    confirmed_by: UUID | None
    created_at: ApiDateTime
    confirmed_at: ApiDateTime | None
    execution_started_at: ApiDateTime | None
    executed_at: ApiDateTime | None
    execution_result: dict[str, JsonValue] | None
    error_message: str | None
    risk_warning: str | None

    @model_validator(mode="before")
    @classmethod
    def sanitize_public_response(cls, value: Any) -> Any:
        if hasattr(value, "before_snapshot") and hasattr(value, "execution_result"):
            return cls._safe_data(value, max_bytes=16_384)
        return value

    @classmethod
    def from_confirmation(
        cls,
        confirmation: "ConfirmationTask",
        *,
        max_bytes: int,
    ) -> "ConfirmationTaskResponse":
        return cls.model_validate(cls._safe_data(confirmation, max_bytes=max_bytes))

    @staticmethod
    def _safe_data(
        confirmation: "ConfirmationTask",
        *,
        max_bytes: int,
    ) -> dict[str, object]:
        def safe_summary(value: object | None) -> dict[str, JsonValue] | None:
            if value is None:
                return None
            return audit_summary(value, max_bytes=max_bytes)

        return {
            "id": confirmation.id,
            "agent_task_id": confirmation.agent_task_id,
            "task_step_id": confirmation.task_step_id,
            "operation_type": confirmation.operation_type,
            "target_type": confirmation.target_type,
            "target_id": confirmation.target_id,
            "risk_level": ToolRiskLevel(confirmation.risk_level),
            "before_snapshot": safe_summary(confirmation.before_snapshot),
            "after_snapshot": safe_summary(confirmation.after_snapshot),
            "status": ConfirmationStatus(confirmation.status),
            "idempotency_key": confirmation.idempotency_key,
            "created_by": confirmation.created_by,
            "confirmed_by": confirmation.confirmed_by,
            "created_at": confirmation.created_at,
            "confirmed_at": confirmation.confirmed_at,
            "execution_started_at": confirmation.execution_started_at,
            "executed_at": confirmation.executed_at,
            "execution_result": safe_summary(confirmation.execution_result),
            "error_message": (
                redact_sensitive(confirmation.error_message)[:1000]
                if confirmation.error_message
                else None
            ),
            "risk_warning": (
                redact_sensitive(confirmation.risk_warning)[:1000]
                if confirmation.risk_warning
                else None
            ),
        }


class ConfirmationSummary(BaseModel):
    id: UUID
    agent_task_id: UUID
    operation_type: str
    target_type: str
    target_id: str | None
    risk_level: ToolRiskLevel
    status: ConfirmationStatus
    created_at: ApiDateTime
