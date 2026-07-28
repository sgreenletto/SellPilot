from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from sellpilot.core.enums import TaskStatus, TaskStepStatus, TaskType, WorkflowNodeType
from sellpilot.schemas.common import ApiDateTime
from sellpilot.workflows.contracts import TaskExecutionResult, WorkflowMetadata


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_name: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    workflow_input: dict[str, JsonValue] = Field(default_factory=dict)


class AgentTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_type: str
    workflow_name: str
    workflow_version: str
    parent_task_id: UUID | None
    status: TaskStatus
    current_step: str | None
    current_node: str | None
    result: dict[str, JsonValue] | None
    error_code: str | None
    error_message: str | None
    retry_count: int
    task_attempt: int
    request_id: str
    created_by: UUID
    created_at: ApiDateTime
    started_at: ApiDateTime | None
    finished_at: ApiDateTime | None


class TaskStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    sequence: int
    node_name: str
    node_type: WorkflowNodeType
    status: TaskStepStatus
    attempt_count: int
    input_summary: dict[str, JsonValue] | None
    output_summary: dict[str, JsonValue] | None
    error_code: str | None
    error_message: str | None
    tool_call_id: UUID | None
    confirmation_id: UUID | None
    metadata: dict[str, JsonValue] | None = Field(validation_alias="step_metadata")
    started_at: ApiDateTime | None
    completed_at: ApiDateTime | None


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


__all__ = [
    "AgentTaskResponse",
    "LongTaskReference",
    "TaskCreateRequest",
    "TaskExecutionResult",
    "TaskStatus",
    "TaskStepResponse",
    "TaskStepStatus",
    "TaskType",
    "WorkflowMetadata",
]
