import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.core.enums import OperationStatus, TaskStatus
from sellpilot.core.exceptions import (
    ErrorCode,
    ParameterError,
    ResourceNotFoundError,
    StateConflictError,
    TaskRuntimeError,
)
from sellpilot.core.transitions import validate_task_transition
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.repositories.operation_log import OperationLogRepository
from sellpilot.repositories.task import TaskRepository
from sellpilot.tools.sanitization import audit_summary, contains_sensitive_values
from sellpilot.workflows.contracts import WorkflowDefinition


class TaskService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings
        self.tasks = TaskRepository(session)
        self.operation_logs = OperationLogRepository(session)

    async def create_internal_task(
        self,
        *,
        task_type: str,
        user_input: str,
        created_by: UUID,
        request_id: str = "00000000-0000-0000-0000-000000000000",
    ) -> AgentTask:
        try:
            parsed_input = json.loads(user_input)
            if not isinstance(parsed_input, dict):
                parsed_input = {"value": parsed_input}
        except (TypeError, json.JSONDecodeError):
            parsed_input = {"value": user_input}
        return await self.tasks.add(
            AgentTask(
                task_type=str(task_type),
                user_input=user_input,
                workflow_name=str(task_type),
                workflow_version="1.0.0",
                workflow_input=parsed_input,
                serialized_state={},
                task_attempt=0,
                request_id=request_id,
                created_by=created_by,
                status=TaskStatus.PENDING,
            )
        )

    async def create_workflow_task(
        self,
        definition: WorkflowDefinition,
        *,
        workflow_input: dict[str, object],
        created_by: UUID,
        request_id: str,
        parent_task_id: UUID | None = None,
    ) -> AgentTask:
        try:
            validated = definition.input_schema.model_validate(workflow_input)
        except ValidationError as exc:
            raise ParameterError("Workflow input is invalid") from exc
        trusted_input = validated.model_dump(mode="json")
        if contains_sensitive_values(trusted_input):
            raise ParameterError(
                "Workflow inputs cannot persist secrets; use server-side secret references"
            )
        max_bytes = self.settings.task_state_max_bytes if self.settings else 65_536
        if (
            len(
                json.dumps(
                    trusted_input,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            > max_bytes
        ):
            raise TaskRuntimeError(
                "Workflow input exceeds the configured state size limit",
                code=ErrorCode.TASK_STATE_TOO_LARGE,
                status_code=422,
            )
        task = await self.tasks.add(
            AgentTask(
                task_type=definition.task_type,
                user_input=json.dumps(
                    trusted_input,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                workflow_name=definition.name,
                workflow_version=definition.version,
                workflow_input=trusted_input,
                serialized_state={},
                parent_task_id=parent_task_id,
                current_node=definition.entry_node,
                current_step=definition.entry_node,
                task_attempt=0,
                request_id=request_id,
                created_by=created_by,
                status=TaskStatus.PENDING,
            )
        )
        await self._log_event(
            task,
            action="task_created",
            details={
                "workflow_name": definition.name,
                "workflow_version": definition.version,
                "input_summary": audit_summary(trusted_input, max_bytes=min(max_bytes, 16_384)),
            },
        )
        return task

    async def get(self, task_id: UUID, *, user_id: UUID | None = None) -> AgentTask:
        task = (
            await self.tasks.get_owned(task_id, user_id)
            if user_id is not None
            else await self.tasks.get(task_id)
        )
        if task is None:
            raise ResourceNotFoundError("Agent task not found")
        return task

    async def list(
        self,
        page: int,
        page_size: int,
        *,
        user_id: UUID | None = None,
        status: TaskStatus | None = None,
        workflow_name: str | None = None,
        task_type: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[AgentTask], int]:
        return await self.tasks.list(
            page,
            page_size,
            user_id=user_id,
            status=status,
            workflow_name=workflow_name,
            task_type=task_type,
            created_from=created_from,
            created_to=created_to,
        )

    def _transition(
        self,
        task: AgentTask,
        target: TaskStatus,
        *,
        allow_retry: bool = False,
    ) -> None:
        current = TaskStatus(task.status)
        validate_task_transition(current, target, allow_retry=allow_retry)
        task.status = target

    async def start(self, task_id: UUID) -> AgentTask:
        task = await self.get(task_id)
        self._transition(task, TaskStatus.RUNNING)
        task.started_at = task.started_at or datetime.now(UTC)
        return task

    async def wait_for_confirmation(self, task_id: UUID) -> AgentTask:
        task = await self.get(task_id)
        self._transition(task, TaskStatus.WAITING_CONFIRMATION)
        return task

    async def update_current_step(self, task_id: UUID, step_name: str) -> AgentTask:
        task = await self.get(task_id)
        if TaskStatus(task.status) is not TaskStatus.RUNNING:
            raise StateConflictError("Current step can only be updated for a running task")
        task.current_step = step_name
        task.current_node = step_name
        return task

    async def complete(self, task_id: UUID, result: dict[str, Any]) -> AgentTask:
        task = await self.get(task_id)
        self._transition(task, TaskStatus.SUCCEEDED)
        task.result = result
        task.error_code = None
        task.error_message = None
        task.finished_at = datetime.now(UTC)
        return task

    async def fail(self, task_id: UUID, error_code: str, error_message: str) -> AgentTask:
        task = await self.get(task_id)
        self._transition(task, TaskStatus.FAILED)
        task.error_code = error_code
        task.error_message = error_message
        task.finished_at = datetime.now(UTC)
        return task

    async def _log_event(
        self,
        task: AgentTask,
        *,
        action: str,
        details: dict[str, Any] | None = None,
        task_step_id: UUID | None = None,
        confirmation_id: UUID | None = None,
        tool_call_id: UUID | None = None,
        status: OperationStatus = OperationStatus.SUCCEEDED,
    ) -> OperationLog:
        return await self.operation_logs.add(
            OperationLog(
                actor_id=task.created_by,
                action=action,
                target_type="agent_task",
                target_id=str(task.id),
                request_id=task.request_id,
                agent_task_id=task.id,
                task_step_id=task_step_id,
                confirmation_task_id=confirmation_id,
                tool_call_id=tool_call_id,
                caller_type="workflow",
                is_mock=(
                    self.settings.platform_adapter == "mock" if self.settings is not None else False
                ),
                details=details,
                status=status,
            )
        )
