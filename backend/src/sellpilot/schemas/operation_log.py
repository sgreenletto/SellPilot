from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

from sellpilot.core.enums import OperationStatus
from sellpilot.schemas.common import ApiDateTime
from sellpilot.tools.sanitization import audit_summary


class OperationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    description: str
    status: OperationStatus
    task_id: UUID | None
    task_step_id: UUID | None
    tool_call_id: UUID | None
    confirmation_id: UUID | None
    actor: dict[str, JsonValue] | None
    request_id: str
    created_at: ApiDateTime
    metadata: dict[str, JsonValue] | None

    @model_validator(mode="before")
    @classmethod
    def sanitize_public_response(cls, value: Any) -> Any:
        if hasattr(value, "details") and hasattr(value, "agent_task_id"):
            return cls._safe_data(value, max_bytes=16_384)
        return value

    @classmethod
    def from_operation_log(
        cls,
        operation_log: Any,
        *,
        max_bytes: int,
    ) -> "OperationLogResponse":
        return cls.model_validate(cls._safe_data(operation_log, max_bytes=max_bytes))

    @staticmethod
    def _safe_data(operation_log: Any, *, max_bytes: int) -> dict[str, object]:
        details = audit_summary(operation_log.details, max_bytes=max_bytes)
        description = str(details.get("message") or details.get("summary") or operation_log.action)
        return {
            "id": operation_log.id,
            "event_type": operation_log.action,
            "description": description[:1000],
            "status": OperationStatus(operation_log.status),
            "task_id": operation_log.agent_task_id,
            "task_step_id": operation_log.task_step_id,
            "tool_call_id": operation_log.tool_call_id,
            "confirmation_id": operation_log.confirmation_task_id,
            "actor": (
                {"id": str(operation_log.actor_id)} if operation_log.actor_id is not None else None
            ),
            "request_id": operation_log.request_id,
            "created_at": operation_log.created_at,
            "metadata": details,
        }


__all__ = ["OperationLogResponse"]
