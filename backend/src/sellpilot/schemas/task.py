from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from sellpilot.core.enums import TaskStatus
from sellpilot.schemas.common import ApiDateTime


class AgentTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_type: str
    user_input: str
    status: TaskStatus
    current_step: str | None
    result: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    retry_count: int
    created_by: UUID
    created_at: ApiDateTime
    started_at: ApiDateTime | None
    finished_at: ApiDateTime | None


class LongTaskReference(BaseModel):
    task_id: UUID
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    current_step: str | None
    message: str | None
    error_code: str | None
    created_at: ApiDateTime
    started_at: ApiDateTime | None
    completed_at: ApiDateTime | None
