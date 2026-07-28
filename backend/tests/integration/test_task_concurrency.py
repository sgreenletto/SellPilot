import asyncio
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict

from sellpilot.core.enums import TaskStepStatus, TaskType, ToolRiskLevel, WorkflowNodeType
from sellpilot.core.exceptions import ErrorCode, TaskRuntimeError
from sellpilot.db.models.user import User
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


class ConcurrentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int


class ConcurrentOutput(ConcurrentInput):
    pass


def definition(handler) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="concurrent_task",
        version="1.0.0",
        description="Test-only concurrent workflow",
        task_type=TaskType.DIAGNOSTIC,
        input_schema=ConcurrentInput,
        output_schema=ConcurrentOutput,
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


async def create_task(session_factory, settings, workflow):
    async with session_factory() as session:
        user = User(
            username=f"task-concurrency-{uuid4()}",
            password_hash="test-hash",
            role="ADMIN",
        )
        session.add(user)
        await session.flush()
        task = await TaskService(session, settings).create_workflow_task(
            workflow,
            workflow_input={"value": 9},
            created_by=user.id,
            request_id=str(uuid4()),
        )
        await session.commit()
        return task.id, user.id


async def test_concurrent_run_has_single_execution_owner(session_factory, test_settings):
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def handler(context: TaskExecutionContext):
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return NodeExecutionResult(output={"value": context.workflow_input["value"]})

    workflow = definition(handler)
    workflows = WorkflowRegistry(test_settings)
    workflows.register(workflow)
    tools = build_tool_registry(test_settings)
    task_id, user_id = await create_task(session_factory, test_settings, workflow)

    async with session_factory() as first_session, session_factory() as second_session:
        first = asyncio.create_task(
            TaskRunner(workflows, tools, first_session, test_settings).run(
                task_id,
                user_id=user_id,
            )
        )
        await asyncio.wait_for(entered.wait(), timeout=2)
        with pytest.raises(TaskRuntimeError) as exc_info:
            await TaskRunner(workflows, tools, second_session, test_settings).run(
                task_id,
                user_id=user_id,
            )
        assert exc_info.value.code == ErrorCode.TASK_ALREADY_RUNNING
        release.set()
        result = await first
    assert result.status == "succeeded"
    assert calls == 1


async def test_cancelled_running_task_rejects_late_node_result(
    session_factory,
    test_settings,
):
    entered = asyncio.Event()
    release = asyncio.Event()

    async def handler(context: TaskExecutionContext):
        entered.set()
        await release.wait()
        return NodeExecutionResult(output={"value": context.workflow_input["value"]})

    workflow = definition(handler)
    workflows = WorkflowRegistry(test_settings)
    workflows.register(workflow)
    tools = build_tool_registry(test_settings)
    task_id, user_id = await create_task(session_factory, test_settings, workflow)

    async with session_factory() as run_session, session_factory() as cancel_session:
        running = asyncio.create_task(
            TaskRunner(workflows, tools, run_session, test_settings).run(
                task_id,
                user_id=user_id,
            )
        )
        await asyncio.wait_for(entered.wait(), timeout=2)
        cancelled = await TaskRunner(
            workflows,
            tools,
            cancel_session,
            test_settings,
        ).cancel(task_id, user_id=user_id)
        assert cancelled.status == "cancelled"
        release.set()
        with pytest.raises(TaskRuntimeError) as exc_info:
            await running
        assert exc_info.value.code == ErrorCode.TASK_EXECUTION_CONFLICT

    async with session_factory() as verification:
        task = await TaskService(verification).get(task_id, user_id=user_id)
        assert task.status == "cancelled"


async def test_concurrent_retry_reuses_failed_step_once(session_factory, test_settings):
    retry_entered = asyncio.Event()
    retry_release = asyncio.Event()
    calls = 0

    async def handler(context: TaskExecutionContext):
        nonlocal calls
        calls += 1
        if calls == 1:
            return NodeExecutionResult(
                status=TaskStepStatus.FAILED,
                error_code="TRANSIENT",
                error_message="retry me",
                retryable=True,
            )
        retry_entered.set()
        await retry_release.wait()
        return NodeExecutionResult(output={"value": context.workflow_input["value"]})

    workflow = definition(handler)
    workflows = WorkflowRegistry(test_settings)
    workflows.register(workflow)
    tools = build_tool_registry(test_settings)
    task_id, user_id = await create_task(session_factory, test_settings, workflow)
    async with session_factory() as initial_session:
        await TaskRunner(workflows, tools, initial_session, test_settings).run(
            task_id,
            user_id=user_id,
        )

    async with session_factory() as first_session, session_factory() as second_session:
        first = asyncio.create_task(
            TaskRunner(workflows, tools, first_session, test_settings).retry(
                task_id,
                user_id=user_id,
            )
        )
        await asyncio.wait_for(retry_entered.wait(), timeout=2)
        with pytest.raises(TaskRuntimeError):
            await TaskRunner(workflows, tools, second_session, test_settings).retry(
                task_id,
                user_id=user_id,
            )
        retry_release.set()
        result = await first
    assert result.status == "succeeded"
    assert calls == 2


async def test_concurrent_resume_continues_confirmed_tool_once(
    session_factory,
    test_settings,
):
    write_calls = 0
    finish_calls = 0
    finish_entered = asyncio.Event()
    finish_release = asyncio.Event()

    async def write_handler(payload: ConcurrentInput, _context):
        nonlocal write_calls
        write_calls += 1
        return ConcurrentOutput(value=payload.value)

    tools = ToolRegistry(test_settings)
    tools.register(
        ToolDefinition(
            name="concurrent_resume_write",
            version="1.0.0",
            description="Test-only resume write",
            input_schema=ConcurrentInput,
            output_schema=ConcurrentOutput,
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

    async def build_input(context: TaskExecutionContext):
        return NodeExecutionResult(
            tool_input=context.workflow_input,
            tool_target_type="concurrency",
            tool_target_id="resume",
            idempotency_key=f"resume-{context.task_id}",
        )

    async def finish(context: TaskExecutionContext):
        nonlocal finish_calls
        finish_calls += 1
        finish_entered.set()
        await finish_release.wait()
        return NodeExecutionResult(output=dict(context.state["last_output"]))

    workflow = WorkflowDefinition(
        name="concurrent_resume",
        version="1.0.0",
        description="Test concurrent resume claim",
        task_type=TaskType.DIAGNOSTIC,
        input_schema=ConcurrentInput,
        output_schema=ConcurrentOutput,
        nodes=(
            NodeDefinition(
                name="write",
                node_type=WorkflowNodeType.TOOL,
                handler=build_input,
                tool_name="concurrent_resume_write",
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
    task_id, user_id = await create_task(session_factory, test_settings, workflow)
    async with session_factory() as setup_session:
        waiting = await TaskRunner(
            workflows,
            tools,
            setup_session,
            test_settings,
        ).run(task_id, user_id=user_id)
        confirmation = await build_confirmation_service(
            tools,
            setup_session,
            test_settings,
        ).confirm(waiting.confirmation_id, user_id)
        await setup_session.commit()
        assert confirmation.status == "succeeded"

    async with session_factory() as first_session, session_factory() as second_session:
        first = asyncio.create_task(
            TaskRunner(workflows, tools, first_session, test_settings).resume(
                task_id,
                user_id=user_id,
            )
        )
        await asyncio.wait_for(finish_entered.wait(), timeout=2)
        with pytest.raises(TaskRuntimeError):
            await TaskRunner(
                workflows,
                tools,
                second_session,
                test_settings,
            ).resume(task_id, user_id=user_id)
        finish_release.set()
        result = await first
    assert result.status == "succeeded"
    assert write_calls == 1
    assert finish_calls == 1
