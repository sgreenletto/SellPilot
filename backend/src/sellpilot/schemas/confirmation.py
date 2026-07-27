from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConfirmationTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_task_id: UUID
    operation_type: str
    target_type: str
    target_id: str | None
    risk_level: str
    before_snapshot: dict[str, Any] | None
    after_snapshot: dict[str, Any] | None
    status: str
    idempotency_key: str
    created_by: UUID
    confirmed_by: UUID | None
    created_at: datetime
    confirmed_at: datetime | None
    executed_at: datetime | None
    execution_result: dict[str, Any] | None
    error_message: str | None
