from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from sellpilot.core.enums import ConfirmationStatus, ToolRiskLevel
from sellpilot.schemas.common import ApiDateTime


class ConfirmationTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_task_id: UUID
    operation_type: str
    target_type: str
    target_id: str | None
    risk_level: ToolRiskLevel
    before_snapshot: dict[str, Any] | None
    after_snapshot: dict[str, Any] | None
    status: ConfirmationStatus
    idempotency_key: str
    created_by: UUID
    confirmed_by: UUID | None
    created_at: ApiDateTime
    confirmed_at: ApiDateTime | None
    executed_at: ApiDateTime | None
    execution_result: dict[str, Any] | None
    error_message: str | None


class ConfirmationSummary(BaseModel):
    id: UUID
    agent_task_id: UUID
    operation_type: str
    target_type: str
    target_id: str | None
    risk_level: ToolRiskLevel
    status: ConfirmationStatus
    created_at: ApiDateTime
