from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.enums import TaskStatus, TaskStepStatus
from sellpilot.core.exceptions import ResourceNotFoundError, StateConflictError
from sellpilot.core.transitions import validate_task_transition
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.agent_task_step import AgentTaskStep
from sellpilot.repositories.task import TaskRepository


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.tasks = TaskRepository(session)

    async def create_internal_task(
        self, *, task_type: str, user_input: str, created_by: UUID
    ) -> AgentTask:
        return await self.tasks.add(
            AgentTask(
                task_type=task_type,
                user_input=user_input,
                created_by=created_by,
                status=TaskStatus.PENDING,
            )
        )

    async def get(self, task_id: UUID) -> AgentTask:
        task = await self.tasks.get(task_id)
        if task is None:
            raise ResourceNotFoundError("Agent task not found")
        return task

    async def list(self, page: int, page_size: int) -> tuple[list[AgentTask], int]:
        return await self.tasks.list(page, page_size)

    def _transition(self, task: AgentTask, target: TaskStatus) -> None:
        current = TaskStatus(task.status)
        validate_task_transition(current, target)
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

    async def create_steps(
        self,
        task_id: UUID,
        step_names: list[str],
    ) -> list[AgentTaskStep]:
        if len(step_names) != len(set(step_names)):
            raise StateConflictError("Task step names must be unique")
        return await self.tasks.add_steps(
            [
                AgentTaskStep(
                    task_id=task_id,
                    step_name=step_name,
                    status=TaskStepStatus.PENDING,
                )
                for step_name in step_names
            ]
        )

    async def start_step(
        self,
        step_id: UUID,
        *,
        input_summary: dict[str, Any] | None = None,
    ) -> AgentTaskStep:
        step = await self.tasks.get_step(step_id)
        if step is None:
            raise ResourceNotFoundError("Agent task step not found")
        if TaskStepStatus(step.status) is not TaskStepStatus.PENDING:
            raise StateConflictError("Only pending task steps can start")
        step.status = TaskStepStatus.RUNNING
        step.input_summary = input_summary
        step.started_at = datetime.now(UTC)
        await self.update_current_step(step.task_id, step.step_name)
        return step

    async def complete_step(
        self,
        step_id: UUID,
        *,
        output_summary: dict[str, Any] | None = None,
    ) -> AgentTaskStep:
        step = await self.tasks.get_step(step_id)
        if step is None:
            raise ResourceNotFoundError("Agent task step not found")
        if TaskStepStatus(step.status) is not TaskStepStatus.RUNNING:
            raise StateConflictError("Only running task steps can complete")
        step.status = TaskStepStatus.SUCCEEDED
        step.output_summary = output_summary
        step.finished_at = datetime.now(UTC)
        return step

    async def fail_step(self, step_id: UUID, error_message: str) -> AgentTaskStep:
        step = await self.tasks.get_step(step_id)
        if step is None:
            raise ResourceNotFoundError("Agent task step not found")
        if TaskStepStatus(step.status) not in {
            TaskStepStatus.PENDING,
            TaskStepStatus.RUNNING,
        }:
            raise StateConflictError("Only pending or running task steps can fail")
        step.status = TaskStepStatus.FAILED
        step.error_message = error_message
        step.started_at = step.started_at or datetime.now(UTC)
        step.finished_at = datetime.now(UTC)
        return step
