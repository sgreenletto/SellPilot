from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.enums import (
    ConfirmationStatus,
    TaskStatus,
    TaskStepStatus,
    ToolCallStatus,
)
from sellpilot.core.exceptions import AppException
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.repositories.confirmation import ConfirmationRepository
from sellpilot.repositories.task import TaskRepository
from sellpilot.repositories.tool_call import ToolCallRepository
from sellpilot.workflows.contracts import WorkflowDefinition
from sellpilot.workflows.registry import WorkflowRegistry

TaskAction = str


class TaskCenterService:
    def __init__(
        self,
        session: AsyncSession,
        workflow_registry: WorkflowRegistry,
    ) -> None:
        self.tasks = TaskRepository(session)
        self.confirmations = ConfirmationRepository(session)
        self.tool_calls = ToolCallRepository(session)
        self.workflow_registry = workflow_registry

    def _definition(self, task: AgentTask) -> WorkflowDefinition | None:
        try:
            return self.workflow_registry.get(
                task.workflow_name,
                required_version=task.workflow_version,
            )
        except AppException:
            return None

    async def available_actions(self, task: AgentTask) -> list[TaskAction]:
        status = TaskStatus(task.status)
        definition = self._definition(task)
        if status is TaskStatus.PENDING:
            return ["run", "cancel"]
        if status is TaskStatus.RUNNING:
            return ["cancel"]
        if status is TaskStatus.WAITING_CONFIRMATION:
            return await self._waiting_actions(task, definition)
        if status is TaskStatus.FAILED:
            actions: list[TaskAction] = []
            if definition is not None and await self._retryable(task, definition):
                actions.append("retry")
            if definition is not None:
                actions.append("rerun")
            return actions
        if status in {TaskStatus.SUCCEEDED, TaskStatus.CANCELLED}:
            return ["rerun"] if definition is not None else []
        return []

    async def _waiting_actions(
        self,
        task: AgentTask,
        definition: WorkflowDefinition | None,
    ) -> list[TaskAction]:
        confirmations = await self.confirmations.list_by_task(task.id)
        if any(
            ConfirmationStatus(item.status)
            in {
                ConfirmationStatus.PENDING,
                ConfirmationStatus.CONFIRMED,
                ConfirmationStatus.EXECUTING,
            }
            for item in confirmations
        ):
            return ["cancel"]
        step = await self.tasks.latest_step(
            task.id,
            status=TaskStepStatus.WAITING_CONFIRMATION,
        )
        if (
            definition is None
            or not definition.resumable
            or step is None
            or step.confirmation_id is None
            or step.tool_call_id is None
        ):
            return ["cancel"]
        confirmation = await self.confirmations.get(step.confirmation_id)
        tool_call = await self.tool_calls.get(step.tool_call_id)
        if (
            confirmation is not None
            and ConfirmationStatus(confirmation.status) is ConfirmationStatus.SUCCEEDED
            and tool_call is not None
            and ToolCallStatus(tool_call.status) is ToolCallStatus.SUCCEEDED
        ):
            return ["resume", "cancel"]
        return ["cancel"]

    async def _retryable(
        self,
        task: AgentTask,
        definition: WorkflowDefinition,
    ) -> bool:
        step = await self.tasks.latest_step(task.id, status=TaskStepStatus.FAILED)
        if step is None:
            return False
        node = definition.node_map.get(step.step_name)
        return bool(
            node is not None
            and (step.step_metadata or {}).get("retryable") is True
            and step.attempt_count < node.max_attempts
            and task.task_attempt < definition.max_task_attempts
        )


__all__ = ["TaskCenterService"]
