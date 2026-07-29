from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from sellpilot.core.enums import TaskStatus, TaskStepStatus, TaskType, WorkflowNodeType
from sellpilot.core.logging import redact_sensitive
from sellpilot.schemas.common import ApiDateTime
from sellpilot.services.task_result import public_task_result
from sellpilot.tools.sanitization import audit_summary
from sellpilot.workflows.contracts import TaskExecutionResult, WorkflowMetadata


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_name: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    workflow_input: dict[str, JsonValue] = Field(default_factory=dict)


TaskAction = Literal["run", "resume", "retry", "rerun", "cancel"]


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
    updated_at: ApiDateTime
    completed_at: ApiDateTime | None
    waiting_confirmation: bool
    waiting_reason: str | None
    safe_error_summary: str | None
    available_actions: list[TaskAction] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def sanitize_public_response(cls, value: Any) -> Any:
        if hasattr(value, "serialized_state") and hasattr(value, "workflow_input"):
            return cls._safe_data(value, available_actions=[])
        return value

    @classmethod
    def from_task(
        cls,
        task: Any,
        *,
        available_actions: list[TaskAction] | None = None,
    ) -> "AgentTaskResponse":
        return cls.model_validate(cls._safe_data(task, available_actions=available_actions or []))

    @staticmethod
    def _safe_data(
        task: Any,
        *,
        available_actions: list[TaskAction],
    ) -> dict[str, object]:
        task_status = TaskStatus(task.status)
        safe_error = redact_sensitive(task.error_message)[:1000] if task.error_message else None
        return {
            "id": task.id,
            "task_type": task.task_type,
            "workflow_name": task.workflow_name,
            "workflow_version": task.workflow_version,
            "parent_task_id": task.parent_task_id,
            "status": task_status,
            "current_step": task.current_step,
            "current_node": task.current_node,
            "result": (
                public_task_result(task.workflow_name, task.result)
                if task.result is not None
                else None
            ),
            "error_code": task.error_code,
            "error_message": safe_error,
            "retry_count": task.retry_count,
            "task_attempt": task.task_attempt,
            "request_id": task.request_id,
            "created_by": task.created_by,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "finished_at": task.finished_at,
            "updated_at": task.finished_at or task.started_at or task.created_at,
            "completed_at": task.finished_at,
            "waiting_confirmation": task_status is TaskStatus.WAITING_CONFIRMATION,
            "waiting_reason": (
                "等待用户确认" if task_status is TaskStatus.WAITING_CONFIRMATION else None
            ),
            "safe_error_summary": safe_error,
            "available_actions": available_actions,
        }


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

    @model_validator(mode="before")
    @classmethod
    def sanitize_public_response(cls, value: Any) -> Any:
        if hasattr(value, "step_metadata") and hasattr(value, "input_summary"):
            return {
                "id": value.id,
                "task_id": value.task_id,
                "sequence": value.sequence,
                "node_name": value.step_name,
                "node_type": value.node_type,
                "status": value.status,
                "attempt_count": value.attempt_count,
                "input_summary": (
                    audit_summary(value.input_summary, max_bytes=16_384)
                    if value.input_summary is not None
                    else None
                ),
                "output_summary": (
                    audit_summary(value.output_summary, max_bytes=16_384)
                    if value.output_summary is not None
                    else None
                ),
                "error_code": value.error_code,
                "error_message": (
                    redact_sensitive(value.error_message)[:1000] if value.error_message else None
                ),
                "tool_call_id": value.tool_call_id,
                "confirmation_id": value.confirmation_id,
                "step_metadata": (
                    audit_summary(value.step_metadata, max_bytes=4096)
                    if value.step_metadata is not None
                    else None
                ),
                "started_at": value.started_at,
                "completed_at": value.finished_at,
            }
        return value


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
    "TaskAction",
    "TaskCreateRequest",
    "TaskExecutionResult",
    "TaskStatus",
    "TaskStepResponse",
    "TaskStepStatus",
    "TaskType",
    "WorkflowMetadata",
]
