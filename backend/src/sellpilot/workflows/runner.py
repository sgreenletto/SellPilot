import asyncio
import inspect
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.core.enums import (
    ConfirmationStatus,
    OperationStatus,
    TaskStatus,
    TaskStepStatus,
    ToolCallerType,
    ToolCallStatus,
    WorkflowNodeType,
)
from sellpilot.core.exceptions import (
    ErrorCode,
    ResourceNotFoundError,
    TaskRuntimeError,
)
from sellpilot.core.transitions import validate_task_step_transition, validate_task_transition
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.agent_task_step import AgentTaskStep
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.repositories.confirmation import ConfirmationRepository
from sellpilot.repositories.operation_log import OperationLogRepository
from sellpilot.repositories.task import TaskRepository
from sellpilot.repositories.tool_call import ToolCallRepository
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.services.task import TaskService
from sellpilot.tools.contracts import ToolExecutionContext
from sellpilot.tools.executor import ToolExecutor
from sellpilot.tools.registry import ToolRegistry
from sellpilot.tools.sanitization import audit_summary, contains_sensitive_values
from sellpilot.workflows.contracts import (
    NodeDefinition,
    NodeExecutionResult,
    TaskExecutionContext,
    TaskExecutionResult,
    WorkflowDefinition,
)
from sellpilot.workflows.registry import WorkflowRegistry


class TaskRunner:
    """Persistent, bounded workflow executor shared by API and future agents."""

    def __init__(
        self,
        workflow_registry: WorkflowRegistry,
        tool_registry: ToolRegistry,
        session: AsyncSession,
        settings: Settings,
        *,
        runner_id: str | None = None,
    ) -> None:
        self.workflow_registry = workflow_registry
        self.tool_registry = tool_registry
        self.session = session
        self.settings = settings
        self.runner_id = runner_id or f"local-{uuid4()}"
        self.tasks = TaskRepository(session)
        self.confirmations = ConfirmationRepository(session)
        self.tool_calls = ToolCallRepository(session)
        self.operation_logs = OperationLogRepository(session)
        self.tool_executor = ToolExecutor(tool_registry, session, settings)

    async def run(
        self,
        task_id: UUID,
        *,
        user_id: UUID,
        request_id: str | None = None,
    ) -> TaskExecutionResult:
        task = await self._owned_task(task_id, user_id)
        definition = self._definition(task)
        if TaskStatus(task.status) is not TaskStatus.PENDING:
            code = (
                ErrorCode.TASK_ALREADY_RUNNING
                if TaskStatus(task.status) is TaskStatus.RUNNING
                else ErrorCode.TASK_NOT_RUNNABLE
            )
            raise TaskRuntimeError("Task is not pending", code=code)
        task = await self._claim(
            task,
            expected_status=TaskStatus.PENDING,
            increment_attempt=True,
        )
        task.request_id = request_id or task.request_id
        await self._log(task, "task_started", details={"runner_id": self.runner_id})
        await self.session.commit()
        return await self._execute(task, definition)

    async def resume(
        self,
        task_id: UUID,
        *,
        user_id: UUID,
        request_id: str | None = None,
    ) -> TaskExecutionResult:
        task = await self._owned_task(task_id, user_id)
        definition = self._definition(task)
        if not definition.resumable:
            raise TaskRuntimeError(
                "Workflow does not support resume",
                code=ErrorCode.TASK_NOT_RESUMABLE,
            )
        if TaskStatus(task.status) is not TaskStatus.WAITING_CONFIRMATION:
            raise TaskRuntimeError(
                "Task is not waiting for confirmation",
                code=ErrorCode.TASK_NOT_RESUMABLE,
            )
        step = await self.tasks.latest_step(
            task.id,
            status=TaskStepStatus.WAITING_CONFIRMATION,
        )
        if step is None or step.confirmation_id is None or step.tool_call_id is None:
            raise TaskRuntimeError(
                "Task confirmation linkage is incomplete",
                code=ErrorCode.TASK_CONFIRMATION_INVALID,
            )
        confirmation = await self.confirmations.get(step.confirmation_id)
        if confirmation is None or confirmation.agent_task_id != task.id:
            raise TaskRuntimeError(
                "Task confirmation is invalid",
                code=ErrorCode.TASK_CONFIRMATION_INVALID,
            )
        confirmation_status = ConfirmationStatus(confirmation.status)
        if confirmation_status in {
            ConfirmationStatus.PENDING,
            ConfirmationStatus.CONFIRMED,
            ConfirmationStatus.EXECUTING,
        }:
            raise TaskRuntimeError(
                "Task confirmation has not completed",
                code=ErrorCode.TASK_CONFIRMATION_PENDING,
            )
        if confirmation_status is not ConfirmationStatus.SUCCEEDED:
            raise TaskRuntimeError(
                "Task confirmation did not succeed",
                code=ErrorCode.TASK_CONFIRMATION_INVALID,
            )
        tool_call = await self.tool_calls.get(step.tool_call_id)
        if (
            tool_call is None
            or tool_call.task_id != task.id
            or tool_call.task_step_id != step.id
            or tool_call.confirmation_id != confirmation.id
            or ToolCallStatus(tool_call.status) is not ToolCallStatus.SUCCEEDED
        ):
            raise TaskRuntimeError(
                "Confirmed tool result is invalid",
                code=ErrorCode.TASK_CONFIRMATION_INVALID,
            )
        task = await self._claim(
            task,
            expected_status=TaskStatus.WAITING_CONFIRMATION,
            increment_attempt=False,
        )
        task.request_id = request_id or task.request_id
        validate_task_step_transition(
            TaskStepStatus(step.status),
            TaskStepStatus.SUCCEEDED,
        )
        step.status = TaskStepStatus.SUCCEEDED
        step.output_summary = tool_call.output_summary
        step.finished_at = datetime.now(UTC)
        state = dict(task.serialized_state or {})
        state["last_output"] = tool_call.output_summary or {}
        task.serialized_state = self._safe_state(state)
        node = definition.node_map[step.step_name]
        task.current_node = node.next_node
        task.current_step = node.next_node
        await self._log(
            task,
            "task_resumed",
            step=step,
            tool_call_id=tool_call.id,
            confirmation_id=confirmation.id,
        )
        await self._log(
            task,
            "step_succeeded",
            step=step,
            tool_call_id=tool_call.id,
            confirmation_id=confirmation.id,
        )
        await self.session.commit()
        return await self._execute(task, definition)

    async def retry(
        self,
        task_id: UUID,
        *,
        user_id: UUID,
        request_id: str | None = None,
    ) -> TaskExecutionResult:
        task = await self._owned_task(task_id, user_id)
        definition = self._definition(task)
        if TaskStatus(task.status) is not TaskStatus.FAILED:
            raise TaskRuntimeError(
                "Only a failed task can be retried",
                code=ErrorCode.TASK_RETRY_NOT_ALLOWED,
            )
        step = await self.tasks.latest_step(task.id, status=TaskStepStatus.FAILED)
        if step is None:
            raise TaskRuntimeError(
                "Task has no failed step",
                code=ErrorCode.TASK_STEP_NOT_FOUND,
            )
        node = definition.node_map.get(step.step_name)
        retryable = bool((step.step_metadata or {}).get("retryable"))
        if node is None or not retryable:
            raise TaskRuntimeError(
                "Failed step is not retryable",
                code=ErrorCode.TASK_RETRY_NOT_ALLOWED,
            )
        if step.attempt_count >= node.max_attempts:
            raise TaskRuntimeError(
                "Task step reached its attempt limit",
                code=ErrorCode.TASK_ATTEMPT_EXHAUSTED,
            )
        if task.task_attempt >= definition.max_task_attempts:
            raise TaskRuntimeError(
                "Task reached its attempt limit",
                code=ErrorCode.TASK_ATTEMPT_EXHAUSTED,
            )
        task = await self._claim(
            task,
            expected_status=TaskStatus.FAILED,
            increment_attempt=True,
        )
        task.request_id = request_id or task.request_id
        validate_task_step_transition(
            TaskStepStatus(step.status),
            TaskStepStatus.RUNNING,
            allow_retry=True,
        )
        step.status = TaskStepStatus.RUNNING
        step.attempt_count += 1
        step.error_code = None
        step.error_message = None
        step.finished_at = None
        step.started_at = datetime.now(UTC)
        task.current_node = step.step_name
        task.current_step = step.step_name
        await self._log(task, "task_retried", step=step)
        await self._log(task, "step_started", step=step)
        await self.session.commit()
        return await self._execute(task, definition, retry_step=step)

    async def rerun(
        self,
        task_id: UUID,
        *,
        user_id: UUID,
        request_id: str,
    ) -> AgentTask:
        original = await self._owned_task(task_id, user_id)
        if TaskStatus(original.status) not in {
            TaskStatus.SUCCEEDED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            raise TaskRuntimeError(
                "Only a terminal task can be rerun",
                code=ErrorCode.TASK_NOT_RUNNABLE,
            )
        definition = self._definition(original)
        task = await TaskService(self.session, self.settings).create_workflow_task(
            definition,
            workflow_input=original.workflow_input,
            created_by=user_id,
            request_id=request_id,
            parent_task_id=original.id,
        )
        await self._log(
            task,
            "task_rerun_created",
            details={"parent_task_id": str(original.id)},
        )
        return task

    async def cancel(
        self,
        task_id: UUID,
        *,
        user_id: UUID,
        request_id: str | None = None,
    ) -> AgentTask:
        current = await self._owned_task(task_id, user_id)
        if TaskStatus(current.status) not in {
            TaskStatus.PENDING,
            TaskStatus.RUNNING,
            TaskStatus.WAITING_CONFIRMATION,
        }:
            raise TaskRuntimeError(
                "Task cannot be cancelled in its current state",
                code=ErrorCode.TASK_CANCEL_NOT_ALLOWED,
            )
        step = await self.tasks.latest_step(current.id)
        pending_confirmation_id: UUID | None = None
        if (
            step is not None
            and TaskStepStatus(step.status) is TaskStepStatus.WAITING_CONFIRMATION
            and step.confirmation_id is not None
        ):
            confirmation = await self.confirmations.get(step.confirmation_id)
            if (
                confirmation is not None
                and ConfirmationStatus(confirmation.status) is ConfirmationStatus.PENDING
            ):
                pending_confirmation_id = confirmation.id
        task = await self.tasks.cancel_owned(
            task_id,
            user_id=user_id,
            now=datetime.now(UTC),
        )
        if task is None:
            raise TaskRuntimeError(
                "Task cancellation lost the execution race",
                code=ErrorCode.TASK_EXECUTION_CONFLICT,
            )
        if pending_confirmation_id is not None:
            await ConfirmationService(self.session).cancel(
                pending_confirmation_id,
                user_id=user_id,
            )
        task.request_id = request_id or task.request_id
        if step is not None and TaskStepStatus(step.status) in {
            TaskStepStatus.PENDING,
            TaskStepStatus.RUNNING,
            TaskStepStatus.WAITING_CONFIRMATION,
        }:
            validate_task_step_transition(
                TaskStepStatus(step.status),
                TaskStepStatus.CANCELLED,
            )
            step.status = TaskStepStatus.CANCELLED
            step.finished_at = datetime.now(UTC)
        await self._log(task, "task_cancelled", step=step)
        await self.session.commit()
        return task

    async def _execute(
        self,
        task: AgentTask,
        definition: WorkflowDefinition,
        *,
        retry_step: AgentTaskStep | None = None,
    ) -> TaskExecutionResult:
        executed = len(await self.tasks.list_steps(task.id)) - (1 if retry_step is not None else 0)
        current_node = task.current_node or definition.entry_node
        while current_node is not None:
            if executed >= definition.max_steps:
                return await self._fail_task(
                    task,
                    retry_step,
                    ErrorCode.WORKFLOW_FAILED,
                    "Workflow reached its maximum step count",
                    retryable=False,
                )
            await self.session.refresh(task)
            if TaskStatus(task.status) is not TaskStatus.RUNNING or task.execution_token is None:
                raise TaskRuntimeError(
                    "Task execution ownership was lost",
                    code=ErrorCode.TASK_EXECUTION_CONFLICT,
                )
            node = definition.node_map[current_node]
            step = retry_step
            retry_step = None
            if step is None:
                step = AgentTaskStep(
                    task_id=task.id,
                    sequence=await self.tasks.next_sequence(task.id),
                    step_name=node.name,
                    node_type=node.node_type,
                    status=TaskStepStatus.RUNNING,
                    attempt_count=1,
                    input_summary=audit_summary(
                        {
                            "workflow_input": task.workflow_input,
                            "state": task.serialized_state,
                        },
                        max_bytes=self.settings.tool_audit_payload_max_bytes,
                    ),
                    step_metadata={"retryable": False},
                    started_at=datetime.now(UTC),
                )
                await self.tasks.add_step(step)
                await self._log(task, "step_started", step=step)
                await self.session.commit()
            result = await self._execute_node(task, definition, node, step)
            await self.session.refresh(task)
            if TaskStatus(task.status) is not TaskStatus.RUNNING or task.execution_token is None:
                raise TaskRuntimeError(
                    "Task execution ownership was lost",
                    code=ErrorCode.TASK_EXECUTION_CONFLICT,
                )
            if result.confirmation_required:
                return await self._wait_for_confirmation(task, step, result)
            if result.status is TaskStepStatus.FAILED:
                return await self._fail_task(
                    task,
                    step,
                    result.error_code or ErrorCode.WORKFLOW_FAILED,
                    result.error_message or "Workflow node failed",
                    retryable=result.retryable,
                )
            state = dict(task.serialized_state or {})
            state.update(result.state_updates)
            try:
                next_node = self._next_node(node, result, state)
                if next_node is not None:
                    state["last_output"] = result.output
                task.serialized_state = self._safe_state(state)
            except TaskRuntimeError as exc:
                return await self._fail_task(
                    task,
                    step,
                    exc.code,
                    exc.message,
                    retryable=False,
                )
            terminal_node = node.node_type is WorkflowNodeType.FINISH or next_node is None
            if terminal_node:
                try:
                    validated_output = definition.output_schema.model_validate(result.output)
                except ValidationError:
                    return await self._fail_task(
                        task,
                        step,
                        ErrorCode.WORKFLOW_FAILED,
                        "Workflow output failed schema validation",
                        retryable=False,
                    )
                safe_output = validated_output.model_dump(mode="json")
                if contains_sensitive_values(safe_output):
                    return await self._fail_task(
                        task,
                        step,
                        ErrorCode.WORKFLOW_FAILED,
                        "Workflow output contains prohibited sensitive fields",
                        retryable=False,
                    )
                result = result.model_copy(update={"output": safe_output})
            step.output_summary = audit_summary(
                result.output,
                max_bytes=self.settings.tool_audit_payload_max_bytes,
            )
            if result.status is TaskStepStatus.SKIPPED:
                validate_task_step_transition(
                    TaskStepStatus(step.status),
                    TaskStepStatus.SKIPPED,
                )
                step.status = TaskStepStatus.SKIPPED
            else:
                validate_task_step_transition(
                    TaskStepStatus(step.status),
                    TaskStepStatus.SUCCEEDED,
                )
                step.status = TaskStepStatus.SUCCEEDED
            step.finished_at = datetime.now(UTC)
            task.current_node = next_node
            task.current_step = next_node
            await self._log(
                task,
                "step_succeeded",
                step=step,
                tool_call_id=step.tool_call_id,
                confirmation_id=step.confirmation_id,
            )
            await self.session.commit()
            executed += 1
            if terminal_node:
                return await self._complete_task(task, definition, result.output)
            current_node = next_node
        return await self._complete_task(
            task,
            definition,
            dict((task.serialized_state or {}).get("last_output") or {}),
        )

    async def _execute_node(
        self,
        task: AgentTask,
        definition: WorkflowDefinition,
        node: NodeDefinition,
        step: AgentTaskStep,
    ) -> NodeExecutionResult:
        context = TaskExecutionContext(
            task_id=task.id,
            user_id=task.created_by,
            request_id=task.request_id,
            workflow_name=definition.name,
            workflow_version=definition.version,
            workflow_input=task.workflow_input,
            state=task.serialized_state or {},
            current_node=node.name,
            current_step_id=step.id,
            task_attempt=max(1, task.task_attempt),
            metadata={"runner_id": self.runner_id},
        )
        timeout = node.timeout_seconds or self.settings.task_default_node_timeout_seconds
        try:
            node_result = await asyncio.wait_for(
                self._invoke_handler(node, context),
                timeout=timeout,
            )
        except TimeoutError:
            return NodeExecutionResult(
                status=TaskStepStatus.FAILED,
                error_code=ErrorCode.TASK_NODE_TIMEOUT,
                error_message="Workflow node timed out",
                retryable=True,
            )
        except Exception:
            return NodeExecutionResult(
                status=TaskStepStatus.FAILED,
                error_code=ErrorCode.WORKFLOW_FAILED,
                error_message="Workflow node execution failed",
                retryable=True,
            )
        if node.node_type is not WorkflowNodeType.TOOL:
            return node_result
        payload = node_result.tool_input
        if payload is None:
            payload = dict(task.workflow_input)
        tool_definition = self.tool_registry.get(node.tool_name or "")
        idempotency_key = node_result.idempotency_key
        if tool_definition.confirmation_required and idempotency_key is None:
            idempotency_key = f"workflow:{task.id}:{step.id}"
        tool_result = await self.tool_executor.execute(
            node.tool_name or "",
            payload,
            ToolExecutionContext(
                request_id=task.request_id,
                user_id=task.created_by,
                task_id=task.id,
                task_step_id=step.id,
                idempotency_key=idempotency_key,
                caller_type=ToolCallerType.WORKFLOW,
                caller_name=definition.name,
                metadata={"workflow_version": definition.version},
                session=self.session,
            ),
            target_type=node_result.tool_target_type,
            target_id=node_result.tool_target_id,
            before_snapshot=node_result.before_snapshot,
            after_snapshot=node_result.after_snapshot,
            risk_warning=node_result.risk_warning,
        )
        step.tool_call_id = tool_result.tool_call_id
        step.confirmation_id = tool_result.confirmation_id
        if tool_result.confirmation_required:
            return NodeExecutionResult(
                status=TaskStepStatus.WAITING_CONFIRMATION,
                confirmation_required=True,
                confirmation_id=tool_result.confirmation_id,
                error_code=tool_result.error_code,
                error_message=tool_result.error_message,
            )
        if tool_result.status is not ToolCallStatus.SUCCEEDED:
            return NodeExecutionResult(
                status=TaskStepStatus.FAILED,
                error_code=tool_result.error_code or ErrorCode.TOOL_EXECUTION_FAILED,
                error_message=tool_result.error_message or "Workflow tool execution failed",
                retryable=False,
            )
        return node_result.model_copy(
            update={
                "status": TaskStepStatus.SUCCEEDED,
                "output": tool_result.data or {},
            }
        )

    async def _invoke_handler(
        self,
        node: NodeDefinition,
        context: TaskExecutionContext,
    ) -> NodeExecutionResult:
        if node.handler is None:
            return NodeExecutionResult(
                tool_input=context.workflow_input
                if node.node_type is WorkflowNodeType.TOOL
                else None
            )
        if inspect.iscoroutinefunction(node.handler):
            result = await node.handler(context)
        else:
            result = await asyncio.to_thread(node.handler, context)
            if inspect.isawaitable(result):
                result = await result
        return NodeExecutionResult.model_validate(result)

    def _next_node(
        self,
        node: NodeDefinition,
        result: NodeExecutionResult,
        state: dict[str, object],
    ) -> str | None:
        if node.node_type in {WorkflowNodeType.BRANCH, WorkflowNodeType.LOOP}:
            if result.next_node not in set(node.routes.values()):
                raise TaskRuntimeError(
                    "Workflow branch selected an undeclared route",
                    code=ErrorCode.WORKFLOW_DEFINITION_INVALID,
                    status_code=500,
                )
            if node.node_type is WorkflowNodeType.LOOP:
                loop_counts = dict(state.get("_loop_counts") or {})
                count = int(loop_counts.get(node.name, 0)) + 1
                if count > (node.loop_limit or 0):
                    raise TaskRuntimeError(
                        "Workflow loop reached its configured limit",
                        code=ErrorCode.WORKFLOW_FAILED,
                    )
                loop_counts[node.name] = count
                state["_loop_counts"] = loop_counts
            return result.next_node
        if result.next_node is not None and result.next_node != node.next_node:
            raise TaskRuntimeError(
                "Workflow node selected an undeclared next node",
                code=ErrorCode.WORKFLOW_DEFINITION_INVALID,
                status_code=500,
            )
        return result.next_node or node.next_node

    async def _wait_for_confirmation(
        self,
        task: AgentTask,
        step: AgentTaskStep,
        result: NodeExecutionResult,
    ) -> TaskExecutionResult:
        validate_task_step_transition(
            TaskStepStatus(step.status),
            TaskStepStatus.WAITING_CONFIRMATION,
        )
        validate_task_transition(TaskStatus(task.status), TaskStatus.WAITING_CONFIRMATION)
        step.status = TaskStepStatus.WAITING_CONFIRMATION
        step.error_code = None
        step.error_message = None
        task.status = TaskStatus.WAITING_CONFIRMATION
        task.execution_token = None
        task.runner_id = None
        task.lease_expires_at = None
        await self._log(
            task,
            "task_waiting_confirmation",
            step=step,
            tool_call_id=step.tool_call_id,
            confirmation_id=result.confirmation_id,
        )
        await self.session.commit()
        return self._execution_result(
            task,
            current_step_id=step.id,
            confirmation_required=True,
            confirmation_id=result.confirmation_id,
        )

    async def _complete_task(
        self,
        task: AgentTask,
        definition: WorkflowDefinition,
        output: dict[str, object],
    ) -> TaskExecutionResult:
        try:
            validated = definition.output_schema.model_validate(output)
        except ValidationError:
            return await self._fail_task(
                task,
                None,
                ErrorCode.WORKFLOW_FAILED,
                "Workflow output failed schema validation",
                retryable=False,
            )
        safe_output = validated.model_dump(mode="json")
        if contains_sensitive_values(safe_output):
            return await self._fail_task(
                task,
                None,
                ErrorCode.WORKFLOW_FAILED,
                "Workflow output contains prohibited sensitive fields",
                retryable=False,
            )
        validate_task_transition(TaskStatus(task.status), TaskStatus.SUCCEEDED)
        task.status = TaskStatus.SUCCEEDED
        task.result = safe_output
        task.error_code = None
        task.error_message = None
        task.finished_at = datetime.now(UTC)
        task.current_node = None
        task.current_step = None
        task.execution_token = None
        task.runner_id = None
        task.lease_expires_at = None
        await self._log(task, "task_succeeded")
        await self.session.commit()
        return self._execution_result(task)

    async def _fail_task(
        self,
        task: AgentTask,
        step: AgentTaskStep | None,
        error_code: ErrorCode | str,
        error_message: str,
        *,
        retryable: bool,
    ) -> TaskExecutionResult:
        now = datetime.now(UTC)
        if step is not None and TaskStepStatus(step.status) is TaskStepStatus.RUNNING:
            validate_task_step_transition(
                TaskStepStatus(step.status),
                TaskStepStatus.FAILED,
            )
            step.status = TaskStepStatus.FAILED
            step.error_code = str(error_code)
            step.error_message = error_message
            step.step_metadata = {
                **(step.step_metadata or {}),
                "retryable": retryable,
            }
            step.finished_at = now
            await self._log(
                task,
                "step_failed",
                step=step,
                status=OperationStatus.FAILED,
                details={"error_code": str(error_code), "retryable": retryable},
            )
        validate_task_transition(TaskStatus(task.status), TaskStatus.FAILED)
        task.status = TaskStatus.FAILED
        task.error_code = str(error_code)
        task.error_message = error_message
        task.finished_at = now
        task.execution_token = None
        task.runner_id = None
        task.lease_expires_at = None
        await self._log(
            task,
            "task_failed",
            step=step,
            status=OperationStatus.FAILED,
            details={"error_code": str(error_code), "retryable": retryable},
        )
        await self.session.commit()
        return self._execution_result(task, current_step_id=step.id if step else None)

    async def _claim(
        self,
        task: AgentTask,
        *,
        expected_status: TaskStatus,
        increment_attempt: bool,
    ) -> AgentTask:
        now = datetime.now(UTC)
        claimed = await self.tasks.claim_execution(
            task.id,
            user_id=task.created_by,
            expected_status=expected_status,
            execution_token=uuid4(),
            runner_id=self.runner_id,
            now=now,
            lease_expires_at=now + timedelta(seconds=self.settings.task_stale_execution_seconds),
            increment_attempt=increment_attempt,
        )
        if claimed is None:
            raise TaskRuntimeError(
                "Task execution is already owned by another request",
                code=ErrorCode.TASK_EXECUTION_CONFLICT,
            )
        await self.session.commit()
        return claimed

    async def _owned_task(self, task_id: UUID, user_id: UUID) -> AgentTask:
        task = await self.tasks.get_owned(task_id, user_id)
        if task is None:
            raise ResourceNotFoundError("Agent task not found")
        return task

    def _definition(self, task: AgentTask) -> WorkflowDefinition:
        return self.workflow_registry.get(
            task.workflow_name,
            required_version=task.workflow_version,
        )

    def _safe_state(self, state: dict[str, object]) -> dict[str, object]:
        if contains_sensitive_values(state):
            raise TaskRuntimeError(
                "Workflow state contains prohibited sensitive fields",
                code=ErrorCode.WORKFLOW_FAILED,
                status_code=500,
            )
        encoded = json.dumps(
            state,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > self.settings.task_state_max_bytes:
            raise TaskRuntimeError(
                "Workflow state exceeds the configured size limit",
                code=ErrorCode.TASK_STATE_TOO_LARGE,
                status_code=422,
            )
        return state

    async def _log(
        self,
        task: AgentTask,
        action: str,
        *,
        step: AgentTaskStep | None = None,
        tool_call_id: UUID | None = None,
        confirmation_id: UUID | None = None,
        details: dict[str, object] | None = None,
        status: OperationStatus = OperationStatus.SUCCEEDED,
    ) -> None:
        await self.operation_logs.add(
            OperationLog(
                actor_id=task.created_by,
                action=action,
                target_type="agent_task",
                target_id=str(task.id),
                request_id=task.request_id,
                agent_task_id=task.id,
                task_step_id=step.id if step else None,
                confirmation_task_id=confirmation_id,
                tool_call_id=tool_call_id,
                caller_type=ToolCallerType.WORKFLOW,
                is_mock=self.settings.platform_adapter == "mock",
                details=audit_summary(
                    details or {},
                    max_bytes=self.settings.tool_audit_payload_max_bytes,
                ),
                status=status,
            )
        )

    @staticmethod
    def _execution_result(
        task: AgentTask,
        *,
        current_step_id: UUID | None = None,
        confirmation_required: bool = False,
        confirmation_id: UUID | None = None,
    ) -> TaskExecutionResult:
        return TaskExecutionResult(
            task_id=task.id,
            workflow_name=task.workflow_name,
            workflow_version=task.workflow_version,
            status=TaskStatus(task.status),
            current_node=task.current_node,
            current_step_id=current_step_id,
            confirmation_required=confirmation_required,
            confirmation_id=confirmation_id,
            result=task.result,
            error_code=task.error_code,
            error_message=task.error_message,
            task_attempt=task.task_attempt,
            request_id=task.request_id,
            started_at=task.started_at,
            completed_at=task.finished_at,
        )
