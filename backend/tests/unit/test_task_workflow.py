from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import select

from sellpilot.core.enums import (
    ConfirmationStatus,
    TaskStatus,
    TaskStepStatus,
    TaskType,
    ToolRiskLevel,
    WorkflowNodeType,
)
from sellpilot.core.exceptions import (
    ErrorCode,
    ParameterError,
    TaskRuntimeError,
    WorkflowAlreadyRegisteredError,
    WorkflowDisabledError,
    WorkflowNotFoundError,
)
from sellpilot.db.models.agent_task_step import AgentTaskStep
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.db.models.tool_call import ToolCall
from sellpilot.services.task import TaskService
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition
from sellpilot.tools.registry import ToolRegistry
from sellpilot.tools.runtime import build_confirmation_service, build_tool_registry
from sellpilot.workflows.contracts import (
    NodeDefinition,
    NodeExecutionResult,
    TaskExecutionContext,
    WorkflowDefinition,
)
from sellpilot.workflows.registry import WorkflowRegistry
from sellpilot.workflows.runner import TaskRunner
from sellpilot.workflows.runtime import build_workflow_registry


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ValueInput(StrictModel):
    value: int


class ValueOutput(StrictModel):
    value: int


def finish_definition(handler, *, name: str = "test_workflow") -> WorkflowDefinition:
    return WorkflowDefinition(
        name=name,
        version="1.0.0",
        description="Test-only workflow",
        task_type=TaskType.DIAGNOSTIC,
        input_schema=ValueInput,
        output_schema=ValueOutput,
        nodes=(
            NodeDefinition(
                name="finish",
                node_type=WorkflowNodeType.FINISH,
                handler=handler,
                max_attempts=2,
            ),
        ),
        entry_node="finish",
        max_steps=1,
        max_task_attempts=2,
    )


def test_workflow_definition_rejects_invalid_graph_and_unbounded_loop():
    with pytest.raises(ValidationError, match="entry_node"):
        WorkflowDefinition(
            name="invalid_entry",
            version="1.0.0",
            description="invalid",
            task_type=TaskType.DIAGNOSTIC,
            input_schema=ValueInput,
            output_schema=ValueOutput,
            nodes=(NodeDefinition(name="finish", node_type=WorkflowNodeType.FINISH),),
            entry_node="missing",
        )
    with pytest.raises(ValidationError, match="loop_limit"):
        NodeDefinition(
            name="loop",
            node_type=WorkflowNodeType.LOOP,
            handler=lambda _context: NodeExecutionResult(next_node="loop"),
            routes={"again": "loop"},
        )


def test_workflow_registry_is_stable_and_isolated():
    async def handler(context: TaskExecutionContext) -> NodeExecutionResult:
        return NodeExecutionResult(output=context.workflow_input)

    definition = finish_definition(handler)
    first = WorkflowRegistry()
    second = WorkflowRegistry()
    first.register(definition)
    assert first.contains(definition.name)
    assert [item.name for item in first.list()] == ["test_workflow"]
    assert not second.contains(definition.name)
    with pytest.raises(WorkflowAlreadyRegisteredError):
        first.register(definition)
    with pytest.raises(WorkflowNotFoundError):
        second.get(definition.name)
    disabled = definition.model_copy(update={"name": "disabled_workflow", "enabled": False})
    second.register(disabled)
    with pytest.raises(WorkflowDisabledError):
        second.get(disabled.name)


async def test_diagnostic_and_system_health_persist_steps_tool_calls_and_audit(
    session,
    admin_user,
    test_settings,
):
    workflows = build_workflow_registry(test_settings)
    tools = build_tool_registry(test_settings)
    service = TaskService(session, test_settings)

    diagnostic = await service.create_workflow_task(
        workflows.get("diagnostic"),
        workflow_input={"message": "runtime-ok"},
        created_by=admin_user.id,
        request_id=str(uuid4()),
    )
    diagnostic_result = await TaskRunner(
        workflows,
        tools,
        session,
        test_settings,
    ).run(diagnostic.id, user_id=admin_user.id)
    assert diagnostic_result.status is TaskStatus.SUCCEEDED
    assert diagnostic_result.result == {
        "status": "ok",
        "diagnostic": True,
        "message": "runtime-ok",
    }

    health = await service.create_workflow_task(
        workflows.get("system_health_check"),
        workflow_input={},
        created_by=admin_user.id,
        request_id=str(uuid4()),
    )
    health_result = await TaskRunner(
        workflows,
        tools,
        session,
        test_settings,
    ).run(health.id, user_id=admin_user.id)
    assert health_result.status is TaskStatus.SUCCEEDED
    assert health_result.result["status"] == "ok"

    health_steps = list(
        (
            await session.execute(
                select(AgentTaskStep)
                .where(AgentTaskStep.task_id == health.id)
                .order_by(AgentTaskStep.sequence)
            )
        ).scalars()
    )
    assert [step.sequence for step in health_steps] == [1]
    assert all(TaskStepStatus(step.status) is TaskStepStatus.SUCCEEDED for step in health_steps)
    tool_call = await session.scalar(select(ToolCall).where(ToolCall.task_id == health.id))
    assert tool_call is not None
    assert tool_call.task_step_id == health_steps[0].id
    actions = set(
        (
            await session.execute(
                select(OperationLog.action).where(OperationLog.agent_task_id == health.id)
            )
        ).scalars()
    )
    assert {"task_created", "task_started", "step_started", "task_succeeded"} <= actions


async def test_failed_step_retries_in_place_without_replaying_success(
    session,
    admin_user,
    test_settings,
):
    calls = 0

    async def flaky(context: TaskExecutionContext) -> NodeExecutionResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return NodeExecutionResult(
                status=TaskStepStatus.FAILED,
                error_code="TRANSIENT_TEST",
                error_message="Temporary failure",
                retryable=True,
            )
        return NodeExecutionResult(output={"value": context.workflow_input["value"]})

    registry = WorkflowRegistry(test_settings)
    registry.register(finish_definition(flaky))
    task = await TaskService(session, test_settings).create_workflow_task(
        registry.get("test_workflow"),
        workflow_input={"value": 7},
        created_by=admin_user.id,
        request_id=str(uuid4()),
    )
    runner = TaskRunner(
        registry,
        build_tool_registry(test_settings),
        session,
        test_settings,
    )
    first = await runner.run(task.id, user_id=admin_user.id)
    assert first.status is TaskStatus.FAILED
    second = await runner.retry(task.id, user_id=admin_user.id)
    assert second.status is TaskStatus.SUCCEEDED
    assert calls == 2
    steps = await TaskService(session).tasks.list_steps(task.id)
    assert len(steps) == 1
    assert steps[0].attempt_count == 2
    assert TaskStepStatus(steps[0].status) is TaskStepStatus.SUCCEEDED
    with pytest.raises(TaskRuntimeError) as exc_info:
        await runner.retry(task.id, user_id=admin_user.id)
    assert exc_info.value.code == ErrorCode.TASK_RETRY_NOT_ALLOWED


async def test_invalid_workflow_output_fails_task_and_step(
    session,
    admin_user,
    test_settings,
):
    async def invalid_output(_context):
        return NodeExecutionResult(output={"unexpected": True})

    workflow = finish_definition(invalid_output, name="invalid_output")
    registry = WorkflowRegistry(test_settings)
    registry.register(workflow)
    task = await TaskService(session, test_settings).create_workflow_task(
        workflow,
        workflow_input={"value": 1},
        created_by=admin_user.id,
        request_id=str(uuid4()),
    )
    result = await TaskRunner(
        registry,
        build_tool_registry(test_settings),
        session,
        test_settings,
    ).run(task.id, user_id=admin_user.id)
    assert result.status is TaskStatus.FAILED
    steps = await TaskService(session).tasks.list_steps(task.id)
    assert TaskStepStatus(steps[0].status) is TaskStepStatus.FAILED
    assert steps[0].error_code == ErrorCode.WORKFLOW_FAILED


async def test_workflow_input_rejects_secrets_without_persisting_them(
    session,
    admin_user,
    test_settings,
):
    class SecretInput(StrictModel):
        password: str

    async def finish(_context):
        return NodeExecutionResult(output={"value": 1})

    definition = finish_definition(finish).model_copy(
        update={"name": "secret_input", "input_schema": SecretInput}
    )
    with pytest.raises(ParameterError):
        await TaskService(session, test_settings).create_workflow_task(
            definition,
            workflow_input={"password": "NEVER_STORE_THIS"},
            created_by=admin_user.id,
            request_id=str(uuid4()),
        )
    rows = list((await session.execute(select(OperationLog))).scalars())
    assert "NEVER_STORE_THIS" not in repr(rows)


async def test_oversized_serialized_state_fails_safely(
    session,
    admin_user,
    test_settings,
):
    constrained = test_settings.model_copy(update={"task_state_max_bytes": 1024})

    async def expand_state(_context):
        return NodeExecutionResult(
            output={},
            state_updates={"large_value": "x" * 2000},
        )

    async def finish(_context):
        return NodeExecutionResult(output={"value": 1})

    workflow = WorkflowDefinition(
        name="oversized_state",
        version="1.0.0",
        description="Test state limit",
        task_type=TaskType.DIAGNOSTIC,
        input_schema=ValueInput,
        output_schema=ValueOutput,
        nodes=(
            NodeDefinition(
                name="expand",
                node_type=WorkflowNodeType.ACTION,
                handler=expand_state,
                next_node="finish",
            ),
            NodeDefinition(
                name="finish",
                node_type=WorkflowNodeType.FINISH,
                handler=finish,
            ),
        ),
        entry_node="expand",
    )
    workflows = WorkflowRegistry(constrained)
    workflows.register(workflow)
    task = await TaskService(session, constrained).create_workflow_task(
        workflow,
        workflow_input={"value": 1},
        created_by=admin_user.id,
        request_id=str(uuid4()),
    )
    result = await TaskRunner(
        workflows,
        build_tool_registry(constrained),
        session,
        constrained,
    ).run(task.id, user_id=admin_user.id)
    assert result.status is TaskStatus.FAILED
    assert result.error_code == ErrorCode.TASK_STATE_TOO_LARGE
    assert "x" * 100 not in (result.error_message or "")


async def test_write_tool_waits_for_confirmation_and_resume_reuses_tool_call(
    session,
    admin_user,
    test_settings,
):
    calls = 0

    async def write_handler(payload: ValueInput, _context):
        nonlocal calls
        calls += 1
        return ValueOutput(value=payload.value)

    tools = ToolRegistry(test_settings)
    tools.register(
        ToolDefinition(
            name="test_write",
            version="1.0.0",
            description="Test-only write tool",
            input_schema=ValueInput,
            output_schema=ValueOutput,
            risk_level=ToolRiskLevel.WRITE,
            timeout_seconds=1,
            retry_policy=RetryPolicy(
                max_attempts=1,
                initial_delay_ms=0,
                max_delay_ms=0,
                backoff_multiplier=1,
            ),
            idempotent=True,
            expose_to_mcp=False,
            handler=write_handler,
        )
    )

    async def tool_input(context: TaskExecutionContext) -> NodeExecutionResult:
        return NodeExecutionResult(
            tool_input=context.workflow_input,
            tool_target_type="test",
            tool_target_id="target-1",
            idempotency_key=f"task-write-{context.task_id}",
        )

    async def finish(context: TaskExecutionContext) -> NodeExecutionResult:
        return NodeExecutionResult(output=dict(context.state["last_output"]))

    workflow = WorkflowDefinition(
        name="write_confirmation",
        version="1.0.0",
        description="Test-only confirmation workflow",
        task_type=TaskType.DIAGNOSTIC,
        input_schema=ValueInput,
        output_schema=ValueOutput,
        nodes=(
            NodeDefinition(
                name="write",
                node_type=WorkflowNodeType.TOOL,
                handler=tool_input,
                tool_name="test_write",
                next_node="finish",
            ),
            NodeDefinition(
                name="finish",
                node_type=WorkflowNodeType.FINISH,
                handler=finish,
            ),
        ),
        entry_node="write",
        max_steps=2,
        max_task_attempts=1,
    )
    workflows = WorkflowRegistry(test_settings)
    workflows.register(workflow)
    task = await TaskService(session, test_settings).create_workflow_task(
        workflow,
        workflow_input={"value": 11},
        created_by=admin_user.id,
        request_id=str(uuid4()),
    )
    runner = TaskRunner(workflows, tools, session, test_settings)
    waiting = await runner.run(task.id, user_id=admin_user.id)
    assert waiting.status is TaskStatus.WAITING_CONFIRMATION
    assert waiting.confirmation_required
    assert calls == 0
    with pytest.raises(TaskRuntimeError) as pending_error:
        await runner.resume(task.id, user_id=admin_user.id)
    assert pending_error.value.code == ErrorCode.TASK_CONFIRMATION_PENDING

    confirmation = await build_confirmation_service(
        tools,
        session,
        test_settings,
    ).confirm(waiting.confirmation_id, admin_user.id)
    await session.commit()
    assert ConfirmationStatus(confirmation.status) is ConfirmationStatus.SUCCEEDED
    assert calls == 1

    completed = await runner.resume(task.id, user_id=admin_user.id)
    assert completed.status is TaskStatus.SUCCEEDED
    assert completed.result == {"value": 11}
    assert calls == 1
    steps = await TaskService(session).tasks.list_steps(task.id)
    assert len(steps) == 2
    assert steps[0].confirmation_id == waiting.confirmation_id
    with pytest.raises(TaskRuntimeError):
        await runner.resume(task.id, user_id=admin_user.id)

    cancelled_task = await TaskService(session, test_settings).create_workflow_task(
        workflow,
        workflow_input={"value": 12},
        created_by=admin_user.id,
        request_id=str(uuid4()),
    )
    cancelled_wait = await runner.run(cancelled_task.id, user_id=admin_user.id)
    assert cancelled_wait.status is TaskStatus.WAITING_CONFIRMATION
    await runner.cancel(cancelled_task.id, user_id=admin_user.id)
    cancelled_confirmation = await runner.confirmations.get(cancelled_wait.confirmation_id)
    assert ConfirmationStatus(cancelled_confirmation.status) is ConfirmationStatus.CANCELED
    with pytest.raises(TaskRuntimeError):
        await runner.resume(cancelled_task.id, user_id=admin_user.id)
    assert calls == 1
