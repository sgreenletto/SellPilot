from types import SimpleNamespace
from uuid import uuid4

from pydantic import BaseModel

from sellpilot.core.enums import (
    ConfirmationStatus,
    TaskStatus,
    TaskType,
    ToolCallStatus,
    WorkflowNodeType,
)
from sellpilot.services.task_center import TaskCenterService
from sellpilot.workflows.contracts import NodeDefinition, WorkflowDefinition
from sellpilot.workflows.registry import WorkflowRegistry


class EmptyContract(BaseModel):
    pass


class StubTasks:
    step = None

    async def latest_step(self, *_args, **_kwargs):
        return self.step


class StubConfirmations:
    items = []
    item = None

    async def list_by_task(self, _task_id):
        return self.items

    async def get(self, _confirmation_id):
        return self.item


class StubToolCalls:
    item = None

    async def get(self, _tool_call_id):
        return self.item


def definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        name="task_center_test",
        version="1.0.0",
        description="Task center action test workflow",
        task_type=TaskType.DIAGNOSTIC,
        input_schema=EmptyContract,
        output_schema=EmptyContract,
        nodes=(
            NodeDefinition(
                name="work",
                node_type=WorkflowNodeType.TOOL,
                tool_name="system_health",
                next_node="finish",
                max_attempts=2,
            ),
            NodeDefinition(name="finish", node_type=WorkflowNodeType.FINISH),
        ),
        entry_node="work",
        max_task_attempts=3,
    )


def task(status: TaskStatus):
    return SimpleNamespace(
        id=uuid4(),
        status=status,
        workflow_name="task_center_test",
        workflow_version="1.0.0",
        task_attempt=1,
    )


async def test_available_actions_cover_all_task_states_and_retry_limits():
    registry = WorkflowRegistry()
    registry.register(definition())
    service = TaskCenterService.__new__(TaskCenterService)
    service.workflow_registry = registry
    service.tasks = StubTasks()
    service.confirmations = StubConfirmations()
    service.tool_calls = StubToolCalls()

    assert await service.available_actions(task(TaskStatus.PENDING)) == ["run", "cancel"]
    assert await service.available_actions(task(TaskStatus.RUNNING)) == ["cancel"]
    assert await service.available_actions(task(TaskStatus.SUCCEEDED)) == ["rerun"]
    assert await service.available_actions(task(TaskStatus.CANCELLED)) == ["rerun"]

    failed = task(TaskStatus.FAILED)
    service.tasks.step = SimpleNamespace(
        step_name="work",
        step_metadata={"retryable": True},
        attempt_count=1,
    )
    assert await service.available_actions(failed) == ["retry", "rerun"]
    service.tasks.step.attempt_count = 2
    assert await service.available_actions(failed) == ["rerun"]
    service.tasks.step.attempt_count = 1
    failed.task_attempt = 3
    assert await service.available_actions(failed) == ["rerun"]

    waiting = task(TaskStatus.WAITING_CONFIRMATION)
    service.confirmations.items = [SimpleNamespace(status=ConfirmationStatus.PENDING)]
    assert await service.available_actions(waiting) == ["cancel"]
    confirmation_id = uuid4()
    tool_call_id = uuid4()
    service.confirmations.items = [SimpleNamespace(status=ConfirmationStatus.SUCCEEDED)]
    service.tasks.step = SimpleNamespace(
        confirmation_id=confirmation_id,
        tool_call_id=tool_call_id,
    )
    service.confirmations.item = SimpleNamespace(status=ConfirmationStatus.SUCCEEDED)
    service.tool_calls.item = SimpleNamespace(status=ToolCallStatus.SUCCEEDED)
    assert await service.available_actions(waiting) == ["resume", "cancel"]


async def test_available_actions_degrade_safely_when_workflow_is_missing():
    service = TaskCenterService.__new__(TaskCenterService)
    service.workflow_registry = WorkflowRegistry()
    service.tasks = StubTasks()
    service.confirmations = StubConfirmations()
    service.tool_calls = StubToolCalls()

    missing = task(TaskStatus.FAILED)
    assert await service.available_actions(missing) == []
