import asyncio
import hashlib
import inspect
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from pydantic import BaseModel, JsonValue, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.core.enums import (
    ConfirmationStatus,
    OperationStatus,
    ToolCallerType,
    ToolCallStatus,
    ToolRiskLevel,
)
from sellpilot.core.exceptions import (
    AppException,
    ErrorCode,
    ParameterError,
    ToolConfirmationInvalidError,
    ToolFailureError,
)
from sellpilot.core.logging import redact_sensitive
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.db.models.tool_call import ToolCall
from sellpilot.repositories.operation_log import OperationLogRepository
from sellpilot.repositories.tool_call import ToolCallRepository
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.tools.contracts import (
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionResult,
)
from sellpilot.tools.registry import ToolRegistry
from sellpilot.tools.sanitization import (
    audit_summary,
    contains_sensitive_values,
    redact_nested,
)

TOOL_CONFIRMATION_OPERATION = "tool.execute"
SleepFunction = Callable[[float], Awaitable[None]]


class ToolExecutor:
    """Single execution path for API, workflow, agent, MCP, system and tests."""

    def __init__(
        self,
        registry: ToolRegistry,
        session: AsyncSession,
        settings: Settings,
        *,
        sleep: SleepFunction = asyncio.sleep,
    ) -> None:
        self.registry = registry
        self.session = session
        self.settings = settings
        self.tool_calls = ToolCallRepository(session)
        self.operation_logs = OperationLogRepository(session)
        self._sleep = sleep

    async def execute(
        self,
        name: str,
        payload: dict[str, JsonValue],
        context: ToolExecutionContext,
        *,
        target_type: str = "tool",
        target_id: str | None = None,
        before_snapshot: dict[str, JsonValue] | None = None,
        after_snapshot: dict[str, JsonValue] | None = None,
        risk_warning: str | None = None,
    ) -> ToolExecutionResult:
        definition = (
            self.registry.get_mcp(name)
            if context.caller_type is ToolCallerType.MCP
            else self.registry.get(name)
        )
        self._validate_context(definition, context)
        started_at = datetime.now(UTC)
        started = perf_counter()
        input_digest = self._input_digest(
            definition,
            payload,
            user_id=context.user_id,
            target_type=target_type,
            target_id=target_id,
        )
        tool_call = await self.tool_calls.add(
            ToolCall(
                task_id=context.task_id,
                task_step_id=context.task_step_id,
                user_id=context.user_id,
                tool_name=definition.name,
                tool_version=definition.version,
                risk_level=definition.risk_level,
                caller_type=context.caller_type,
                caller_name=context.caller_name,
                request_id=context.request_id,
                idempotency_key=context.idempotency_key,
                input_digest=input_digest,
                status=ToolCallStatus.PENDING,
                input_summary=audit_summary(
                    payload,
                    extra_sensitive_fields=definition.sensitive_input_fields,
                    max_bytes=self.settings.tool_audit_payload_max_bytes,
                ),
                attempt_count=0,
                started_at=started_at,
            )
        )
        try:
            validated_input = definition.input_schema.model_validate(payload)
        except ValidationError:
            return await self._finalize(
                tool_call,
                definition,
                context,
                status=ToolCallStatus.FAILED,
                error_code=ErrorCode.TOOL_INPUT_INVALID,
                error_message="Tool input failed schema validation",
                attempt_count=0,
                attempt_history=[],
                started=started,
                target_type=target_type,
                target_id=target_id,
            )
        input_digest = self._input_digest(
            definition,
            validated_input.model_dump(mode="json"),
            user_id=context.user_id,
            target_type=target_type,
            target_id=target_id,
        )
        tool_call.input_digest = input_digest

        if definition.confirmation_required:
            try:
                return await self._request_confirmation(
                    tool_call,
                    definition,
                    validated_input,
                    context,
                    input_digest=input_digest,
                    target_type=target_type,
                    target_id=target_id,
                    before_snapshot=before_snapshot,
                    after_snapshot=after_snapshot,
                    risk_warning=risk_warning,
                    started=started,
                )
            except AppException as exc:
                return await self._finalize(
                    tool_call,
                    definition,
                    context,
                    status=ToolCallStatus.BLOCKED,
                    error_code=str(exc.code),
                    error_message=exc.message,
                    attempt_count=0,
                    attempt_history=[],
                    started=started,
                    target_type=target_type,
                    target_id=target_id,
                )

        return await self._run_handler(
            tool_call,
            definition,
            validated_input,
            context,
            target_type=target_type,
            target_id=target_id,
            started=started,
        )

    async def execute_confirmation(self, confirmation: ConfirmationTask) -> dict[str, JsonValue]:
        if (
            ConfirmationStatus(confirmation.status) is not ConfirmationStatus.EXECUTING
            or confirmation.confirmed_by is None
            or confirmation.tool_name is None
            or confirmation.tool_version is None
            or confirmation.tool_input is None
            or confirmation.input_digest is None
            or confirmation.request_id is None
        ):
            raise ToolConfirmationInvalidError()
        definition = self.registry.get(
            confirmation.tool_name,
            required_version=confirmation.tool_version,
        )
        if definition.risk_level is ToolRiskLevel.READ:
            raise ToolConfirmationInvalidError("Read tools cannot execute from a confirmation")
        expected_digest = self._input_digest(
            definition,
            confirmation.tool_input,
            user_id=confirmation.created_by,
            target_type=confirmation.target_type,
            target_id=confirmation.target_id,
        )
        if expected_digest != confirmation.input_digest:
            raise ToolConfirmationInvalidError("Confirmed tool payload digest does not match")
        try:
            validated_input = definition.input_schema.model_validate(confirmation.tool_input)
        except ValidationError as exc:
            raise ToolConfirmationInvalidError(
                "Confirmed tool input no longer matches its schema"
            ) from exc

        linked_calls = await self.tool_calls.list_by_confirmation(confirmation.id)
        succeeded = next(
            (
                item
                for item in linked_calls
                if ToolCallStatus(item.status) is ToolCallStatus.SUCCEEDED
            ),
            None,
        )
        if succeeded is not None:
            return self._result_from_row(succeeded).model_dump(mode="json")
        if not linked_calls:
            raise ToolConfirmationInvalidError("Confirmation has no linked ToolCall")

        tool_call = linked_calls[0]
        context = ToolExecutionContext(
            request_id=confirmation.request_id,
            user_id=confirmation.created_by,
            task_id=confirmation.agent_task_id,
            confirmation_id=confirmation.id,
            idempotency_key=confirmation.idempotency_key,
            caller_type=ToolCallerType(tool_call.caller_type),
            caller_name=tool_call.caller_name or "confirmation",
            metadata={"confirmed_by": str(confirmation.confirmed_by)},
        )
        tool_call.status = ToolCallStatus.RUNNING
        tool_call.completed_at = None
        await self.session.commit()
        started = perf_counter()
        result = await self._run_handler(
            tool_call,
            definition,
            validated_input,
            context,
            target_type=confirmation.target_type,
            target_id=confirmation.target_id,
            started=started,
            before_snapshot=confirmation.before_snapshot,
            after_snapshot=confirmation.after_snapshot,
        )
        for duplicate in linked_calls[1:]:
            if ToolCallStatus(duplicate.status) is ToolCallStatus.WAITING_CONFIRMATION:
                duplicate.status = result.status
                duplicate.output_summary = tool_call.output_summary
                duplicate.attempt_history = {"attempts": [], "deduplicated": True}
                duplicate.attempt_count = 0
                duplicate.duration_ms = 0
                duplicate.error_code = result.error_code
                duplicate.error_message = result.error_message
                duplicate.completed_at = result.completed_at
        await self.session.flush()
        if result.status is not ToolCallStatus.SUCCEEDED:
            raise ToolFailureError(result.error_message or "Confirmed tool execution failed")
        return result.model_dump(mode="json")

    @staticmethod
    def _validate_context(definition: ToolDefinition, context: ToolExecutionContext) -> None:
        if context.confirmation_id is not None:
            raise ParameterError(
                "confirmation_id is assigned only by the trusted confirmation executor"
            )
        if context.caller_type in {ToolCallerType.AGENT, ToolCallerType.WORKFLOW}:
            if context.task_id is None:
                raise ParameterError("Agent and workflow tool calls require task_id")
        if definition.confirmation_required:
            if context.user_id is None or context.task_id is None:
                raise ParameterError("Confirmed tools require user_id and task_id")
            if context.idempotency_key is None:
                raise ParameterError("Confirmed tools require idempotency_key")

    async def _request_confirmation(
        self,
        tool_call: ToolCall,
        definition: ToolDefinition,
        validated_input: BaseModel,
        context: ToolExecutionContext,
        *,
        input_digest: str,
        target_type: str,
        target_id: str | None,
        before_snapshot: dict[str, JsonValue] | None,
        after_snapshot: dict[str, JsonValue] | None,
        risk_warning: str | None,
        started: float,
    ) -> ToolExecutionResult:
        trusted_input = validated_input.model_dump(mode="json")
        if contains_sensitive_values(
            trusted_input,
            extra_sensitive_fields=definition.sensitive_input_fields,
        ):
            raise ParameterError(
                "Confirmed tool inputs cannot persist secrets; use server-side secret references"
            )
        if definition.risk_level is ToolRiskLevel.HIGH_RISK:
            if before_snapshot is None or after_snapshot is None:
                raise ParameterError(
                    "High-risk confirmations require complete before and after snapshots"
                )
            if not risk_warning or not risk_warning.strip():
                raise ParameterError("High-risk confirmations require a risk warning")
        safe_before = self._confirmation_snapshot(before_snapshot, definition)
        safe_after = self._confirmation_snapshot(after_snapshot, definition)
        confirmation = await ConfirmationService(self.session).create(
            agent_task_id=context.task_id,  # validated by _validate_context
            operation_type=TOOL_CONFIRMATION_OPERATION,
            target_type=target_type,
            target_id=target_id,
            risk_level=definition.risk_level,
            idempotency_key=context.idempotency_key or "",
            created_by=context.user_id,  # validated by _validate_context
            before_snapshot=safe_before,
            after_snapshot=safe_after,
            tool_name=definition.name,
            tool_version=definition.version,
            tool_input=trusted_input,
            input_digest=input_digest,
            request_id=context.request_id,
            risk_warning=redact_sensitive(risk_warning) if risk_warning else None,
        )
        tool_call.confirmation_id = confirmation.id
        confirmation_status = ConfirmationStatus(confirmation.status)
        if confirmation_status is ConfirmationStatus.SUCCEEDED:
            succeeded = await self.tool_calls.get_succeeded_by_confirmation(confirmation.id)
            if succeeded is None:
                raise ToolConfirmationInvalidError(
                    "Succeeded confirmation has no successful ToolCall"
                )
            tool_call.status = ToolCallStatus.SUCCEEDED
            tool_call.output_summary = succeeded.output_summary
            tool_call.attempt_history = {"attempts": [], "idempotent_replay": True}
            tool_call.attempt_count = 0
            tool_call.duration_ms = self._duration_ms(started)
            tool_call.completed_at = datetime.now(UTC)
            await self._write_operation_log(
                tool_call,
                definition,
                context,
                action="tool.idempotent_replay",
                target_type=target_type,
                target_id=target_id,
                status=OperationStatus.SUCCEEDED,
                before_snapshot=safe_before,
                after_snapshot=safe_after,
            )
            await self.session.flush()
            return self._result_from_row(tool_call)
        if confirmation_status in {
            ConfirmationStatus.FAILED,
            ConfirmationStatus.CANCELED,
        }:
            raise ToolConfirmationInvalidError(
                "Existing confirmation is terminal and cannot execute"
            )
        tool_call.status = ToolCallStatus.WAITING_CONFIRMATION
        tool_call.duration_ms = self._duration_ms(started)
        tool_call.completed_at = datetime.now(UTC)
        await self._write_operation_log(
            tool_call,
            definition,
            context,
            action="tool.confirmation_requested",
            target_type=target_type,
            target_id=target_id,
            status=OperationStatus.SUCCEEDED,
            before_snapshot=safe_before,
            after_snapshot=safe_after,
        )
        await self.session.flush()
        return ToolExecutionResult(
            tool_call_id=tool_call.id,
            tool_name=definition.name,
            tool_version=definition.version,
            status=ToolCallStatus.WAITING_CONFIRMATION,
            error_code=ErrorCode.TOOL_CONFIRMATION_REQUIRED,
            error_message="Tool execution requires confirmation",
            confirmation_required=True,
            confirmation_id=confirmation.id,
            attempt_count=0,
            duration_ms=tool_call.duration_ms or 0,
            request_id=context.request_id,
            task_id=context.task_id,
            started_at=tool_call.started_at,
            completed_at=tool_call.completed_at,
        )

    def _confirmation_snapshot(
        self,
        value: dict[str, JsonValue] | None,
        definition: ToolDefinition,
    ) -> dict[str, JsonValue] | None:
        if value is None:
            return None
        summary = audit_summary(
            value,
            extra_sensitive_fields=(
                definition.sensitive_input_fields | definition.sensitive_output_fields
            ),
            max_bytes=self.settings.tool_audit_payload_max_bytes,
        )
        if summary.get("truncated") is True:
            raise ParameterError("Confirmation snapshot exceeds the audit payload limit")
        return summary

    async def _run_handler(
        self,
        tool_call: ToolCall,
        definition: ToolDefinition,
        validated_input: BaseModel,
        context: ToolExecutionContext,
        *,
        target_type: str,
        target_id: str | None,
        started: float,
        before_snapshot: dict[str, JsonValue] | None = None,
        after_snapshot: dict[str, JsonValue] | None = None,
    ) -> ToolExecutionResult:
        tool_call.status = ToolCallStatus.RUNNING
        await self.session.flush()
        attempt_history: list[dict[str, JsonValue]] = []
        final_status = ToolCallStatus.FAILED
        final_code = str(ErrorCode.TOOL_EXECUTION_FAILED)
        final_message = "Tool execution failed"
        output_data: dict[str, JsonValue] | None = None
        attempts = 0

        for attempt in range(1, definition.retry_policy.max_attempts + 1):
            attempts = attempt
            attempt_started = perf_counter()
            try:
                raw_output = await asyncio.wait_for(
                    self._invoke_handler(definition, validated_input, context),
                    timeout=definition.timeout_seconds,
                )
                try:
                    validated_output = definition.output_schema.model_validate(raw_output)
                except ValidationError:
                    final_status = ToolCallStatus.FAILED
                    final_code = str(ErrorCode.TOOL_OUTPUT_INVALID)
                    final_message = "Tool output failed schema validation"
                    attempt_history.append(
                        self._attempt_record(
                            attempt,
                            final_status,
                            final_code,
                            attempt_started,
                        )
                    )
                    break
                safe_output = redact_nested(
                    validated_output,
                    extra_sensitive_fields=definition.sensitive_output_fields,
                )
                output_data = (
                    safe_output if isinstance(safe_output, dict) else {"value": safe_output}
                )
                final_status = ToolCallStatus.SUCCEEDED
                final_code = ""
                final_message = ""
                attempt_history.append(
                    self._attempt_record(attempt, final_status, None, attempt_started)
                )
                break
            except TimeoutError:
                final_status = ToolCallStatus.TIMED_OUT
                final_code = str(ErrorCode.TOOL_TIMEOUT)
                final_message = "Tool execution timed out"
            except AppException as exc:
                final_status = ToolCallStatus.FAILED
                final_code = str(exc.code)
                final_message = self._safe_handler_message(exc)
            except Exception:
                final_status = ToolCallStatus.FAILED
                final_code = str(ErrorCode.TOOL_EXECUTION_FAILED)
                final_message = "Tool execution failed"
            attempt_history.append(
                self._attempt_record(attempt, final_status, final_code, attempt_started)
            )
            if (
                attempt >= definition.retry_policy.max_attempts
                or final_code not in definition.retry_policy.retryable_error_codes
            ):
                break
            delay_ms = min(
                definition.retry_policy.max_delay_ms,
                int(
                    definition.retry_policy.initial_delay_ms
                    * (definition.retry_policy.backoff_multiplier ** (attempt - 1))
                ),
            )
            if delay_ms:
                await self._sleep(delay_ms / 1000)

        if (
            final_status is not ToolCallStatus.SUCCEEDED
            and attempts > 1
            and final_code in definition.retry_policy.retryable_error_codes
        ):
            final_code = str(ErrorCode.TOOL_RETRY_EXHAUSTED)
            final_message = "Tool retry policy was exhausted"

        return await self._finalize(
            tool_call,
            definition,
            context,
            status=final_status,
            data=output_data,
            error_code=final_code or None,
            error_message=final_message or None,
            attempt_count=attempts,
            attempt_history=attempt_history,
            started=started,
            target_type=target_type,
            target_id=target_id,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )

    async def _invoke_handler(
        self,
        definition: ToolDefinition,
        validated_input: BaseModel,
        context: ToolExecutionContext,
    ) -> BaseModel | dict[str, JsonValue]:
        handler_context = context.model_copy(
            update={"session": self.session, "settings": self.settings}
        )
        if inspect.iscoroutinefunction(definition.handler):
            return await definition.handler(validated_input, handler_context)
        result = await asyncio.to_thread(
            definition.handler,
            validated_input,
            handler_context,
        )
        if inspect.isawaitable(result):
            return await result
        return result

    async def _finalize(
        self,
        tool_call: ToolCall,
        definition: ToolDefinition,
        context: ToolExecutionContext,
        *,
        status: ToolCallStatus,
        attempt_count: int,
        attempt_history: list[dict[str, JsonValue]],
        started: float,
        target_type: str,
        target_id: str | None,
        data: dict[str, JsonValue] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        before_snapshot: dict[str, JsonValue] | None = None,
        after_snapshot: dict[str, JsonValue] | None = None,
    ) -> ToolExecutionResult:
        completed_at = datetime.now(UTC)
        duration_ms = self._duration_ms(started)
        tool_call.status = status
        tool_call.output_summary = (
            audit_summary(
                data,
                extra_sensitive_fields=definition.sensitive_output_fields,
                max_bytes=self.settings.tool_audit_payload_max_bytes,
            )
            if data is not None
            else None
        )
        tool_call.attempt_history = {"attempts": attempt_history}
        tool_call.attempt_count = attempt_count
        tool_call.duration_ms = duration_ms
        tool_call.error_code = error_code
        tool_call.error_message = error_message
        tool_call.completed_at = completed_at
        await self._write_operation_log(
            tool_call,
            definition,
            context,
            action="tool.execute",
            target_type=target_type,
            target_id=target_id,
            status=self._operation_status(status),
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
        await self.session.flush()
        return ToolExecutionResult(
            tool_call_id=tool_call.id,
            tool_name=definition.name,
            tool_version=definition.version,
            status=status,
            data=data,
            error_code=error_code,
            error_message=error_message,
            confirmation_required=False,
            confirmation_id=tool_call.confirmation_id,
            attempt_count=attempt_count,
            duration_ms=duration_ms,
            request_id=context.request_id,
            task_id=context.task_id,
            started_at=tool_call.started_at,
            completed_at=completed_at,
        )

    async def _write_operation_log(
        self,
        tool_call: ToolCall,
        definition: ToolDefinition,
        context: ToolExecutionContext,
        *,
        action: str,
        target_type: str,
        target_id: str | None,
        status: OperationStatus,
        before_snapshot: dict[str, JsonValue] | None,
        after_snapshot: dict[str, JsonValue] | None,
    ) -> None:
        await self.operation_logs.add(
            OperationLog(
                actor_id=context.user_id,
                action=action,
                target_type=target_type,
                target_id=target_id or definition.name,
                request_id=context.request_id,
                agent_task_id=context.task_id,
                confirmation_task_id=tool_call.confirmation_id,
                tool_call_id=tool_call.id,
                risk_level=definition.risk_level,
                caller_type=context.caller_type,
                is_mock=self.settings.platform_adapter == "mock",
                details={
                    "tool_name": definition.name,
                    "tool_version": definition.version,
                    "tool_call_id": str(tool_call.id),
                    "status": str(tool_call.status),
                    "attempt_count": tool_call.attempt_count,
                    "error_code": tool_call.error_code,
                    "is_mock": self.settings.platform_adapter == "mock",
                },
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
                status=status,
            )
        )

    @staticmethod
    def _attempt_record(
        attempt: int,
        status: ToolCallStatus,
        error_code: str | None,
        started: float,
    ) -> dict[str, JsonValue]:
        return {
            "attempt": attempt,
            "status": str(status),
            "error_code": error_code,
            "duration_ms": ToolExecutor._duration_ms(started),
        }

    @staticmethod
    def _operation_status(status: ToolCallStatus) -> OperationStatus:
        if status is ToolCallStatus.SUCCEEDED:
            return OperationStatus.SUCCEEDED
        if status is ToolCallStatus.BLOCKED:
            return OperationStatus.BLOCKED
        if status is ToolCallStatus.TIMED_OUT:
            return OperationStatus.TIMED_OUT
        return OperationStatus.FAILED

    @staticmethod
    def _safe_handler_message(exc: AppException) -> str:
        safe_messages = {
            str(ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE): "External service is unavailable",
            str(ErrorCode.MOCK_PLATFORM_FAILED): "Mock platform operation failed",
            str(ErrorCode.DATABASE_UNAVAILABLE): "Database is unavailable",
        }
        return safe_messages.get(str(exc.code), "Tool execution failed")

    @staticmethod
    def _input_digest(
        definition: ToolDefinition,
        payload: object,
        *,
        user_id: UUID | None,
        target_type: str,
        target_id: str | None,
    ) -> str:
        canonical = json.dumps(
            {
                "tool_name": definition.name,
                "tool_version": definition.version,
                "user_id": str(user_id) if user_id else None,
                "target_type": target_type,
                "target_id": target_id,
                "input": payload,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _duration_ms(started: float) -> int:
        return max(0, int((perf_counter() - started) * 1000))

    @staticmethod
    def _result_from_row(tool_call: ToolCall) -> ToolExecutionResult:
        data = tool_call.output_summary
        return ToolExecutionResult(
            tool_call_id=tool_call.id,
            tool_name=tool_call.tool_name,
            tool_version=tool_call.tool_version,
            status=ToolCallStatus(tool_call.status),
            data=data,
            error_code=tool_call.error_code,
            error_message=tool_call.error_message,
            confirmation_required=ToolCallStatus(tool_call.status)
            is ToolCallStatus.WAITING_CONFIRMATION,
            confirmation_id=tool_call.confirmation_id,
            attempt_count=tool_call.attempt_count,
            duration_ms=tool_call.duration_ms or 0,
            request_id=tool_call.request_id,
            task_id=tool_call.task_id,
            started_at=tool_call.started_at,
            completed_at=tool_call.completed_at,
        )
