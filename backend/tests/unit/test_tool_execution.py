import asyncio
import time
from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import select

from sellpilot.core.enums import (
    ConfirmationStatus,
    ToolCallerType,
    ToolCallStatus,
    ToolRiskLevel,
)
from sellpilot.core.exceptions import ErrorCode, ExternalServiceUnavailableError
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.db.models.tool_call import ToolCall
from sellpilot.db.models.user import User
from sellpilot.services.task import TaskService
from sellpilot.tools.contracts import (
    RetryPolicy,
    ToolDefinition,
    ToolExecutionContext,
)
from sellpilot.tools.executor import ToolExecutor
from sellpilot.tools.registry import ToolRegistry
from sellpilot.tools.runtime import build_confirmation_service
from sellpilot.tools.sanitization import audit_summary, redact_nested


class RuntimeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int
    password: str | None = None
    private_note: str | None = None


class RuntimeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: int
    token: str | None = None


async def create_user_and_task(session):
    user = User(username=f"runtime-{uuid4()}", password_hash="test-hash", role="ADMIN")
    session.add(user)
    await session.flush()
    task = await TaskService(session).create_internal_task(
        task_type="diagnostic",
        user_input="tool runtime test",
        created_by=user.id,
    )
    return user, task


def context(
    *,
    user_id=None,
    task_id=None,
    caller_type=ToolCallerType.TEST,
    idempotency_key=None,
):
    return ToolExecutionContext(
        request_id=str(uuid4()),
        user_id=user_id,
        task_id=task_id,
        idempotency_key=idempotency_key,
        caller_type=caller_type,
        caller_name="pytest",
    )


def definition(
    handler,
    *,
    name="runtime_tool",
    version="1.0.0",
    risk=ToolRiskLevel.READ,
    attempts=1,
    retryable=frozenset(),
    timeout=1.0,
    expose_to_mcp=False,
):
    return ToolDefinition(
        name=name,
        version=version,
        description="Runtime test tool",
        input_schema=RuntimeInput,
        output_schema=RuntimeOutput,
        risk_level=risk,
        timeout_seconds=timeout,
        retry_policy=RetryPolicy(
            max_attempts=attempts,
            initial_delay_ms=0,
            max_delay_ms=0,
            backoff_multiplier=2,
            retryable_error_codes=retryable,
        ),
        idempotent=risk is not ToolRiskLevel.READ,
        expose_to_mcp=expose_to_mcp,
        sensitive_input_fields=frozenset({"private_note"}),
        handler=handler,
    )


def executor(session, test_settings, tool_definition, *, sleep=asyncio.sleep):
    registry = ToolRegistry(test_settings)
    registry.register(tool_definition)
    return ToolExecutor(registry, session, test_settings, sleep=sleep), registry


async def test_read_execution_validates_and_persists_safe_audit(session, test_settings):
    user, task = await create_user_and_task(session)
    calls = 0

    async def handler(payload, _context):
        nonlocal calls
        calls += 1
        return {"result": payload.value * 2, "token": "output-secret"}

    runtime, _ = executor(session, test_settings, definition(handler))
    request_context = context(user_id=user.id, task_id=task.id)
    result = await runtime.execute(
        "runtime_tool",
        {"value": 3, "password": "input-secret"},
        request_context,
    )

    assert result.status is ToolCallStatus.SUCCEEDED
    assert result.data == {"result": 6, "token": "[REDACTED]"}
    assert result.request_id == request_context.request_id
    assert result.task_id == task.id
    assert result.attempt_count == 1
    assert calls == 1

    tool_call = await session.get(ToolCall, result.tool_call_id)
    assert tool_call is not None
    assert tool_call.user_id == user.id
    assert tool_call.task_id == task.id
    assert tool_call.request_id == request_context.request_id
    assert tool_call.input_summary["password"] == "[REDACTED]"
    assert tool_call.output_summary["token"] == "[REDACTED]"
    logs = (await session.scalars(select(OperationLog))).all()
    assert len(logs) == 1
    assert logs[0].tool_call_id == tool_call.id
    assert logs[0].is_mock is True
    assert "input-secret" not in str(tool_call.input_summary)
    assert "output-secret" not in str(tool_call.output_summary)


async def test_input_and_output_schema_failures_are_safe(session, test_settings):
    calls = 0

    async def invalid_output(_payload, _context):
        nonlocal calls
        calls += 1
        return {"unexpected": "internal-path-C:\\secret"}

    runtime, _ = executor(session, test_settings, definition(invalid_output))
    invalid_input = await runtime.execute(
        "runtime_tool",
        {"value": "not-an-integer"},
        context(),
    )
    invalid_output_result = await runtime.execute(
        "runtime_tool",
        {"value": 1},
        context(),
    )

    assert invalid_input.error_code == ErrorCode.TOOL_INPUT_INVALID
    assert invalid_input.attempt_count == 0
    assert invalid_output_result.error_code == ErrorCode.TOOL_OUTPUT_INVALID
    assert "C:\\secret" not in (invalid_output_result.error_message or "")
    assert calls == 1


async def test_timeout_is_recorded_without_internal_exception(session, test_settings):
    async def slow_handler(_payload, _context):
        await asyncio.sleep(0.05)
        return {"result": 1}

    runtime, _ = executor(
        session,
        test_settings,
        definition(slow_handler, timeout=0.001),
    )
    result = await runtime.execute("runtime_tool", {"value": 1}, context())
    row = await session.get(ToolCall, result.tool_call_id)

    assert result.status is ToolCallStatus.TIMED_OUT
    assert result.error_code == ErrorCode.TOOL_TIMEOUT
    assert result.error_message == "Tool execution timed out"
    assert row is not None and row.status == ToolCallStatus.TIMED_OUT
    assert "Traceback" not in (row.error_message or "")


async def test_transient_read_failure_retries_then_succeeds(session, test_settings):
    calls = 0
    sleeps: list[float] = []

    async def flaky_handler(payload, _context):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ExternalServiceUnavailableError()
        return {"result": payload.value}

    async def fake_sleep(delay):
        sleeps.append(delay)

    runtime, _ = executor(
        session,
        test_settings,
        definition(
            flaky_handler,
            attempts=2,
            retryable=frozenset({ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE}),
        ),
        sleep=fake_sleep,
    )
    result = await runtime.execute("runtime_tool", {"value": 4}, context())

    assert result.status is ToolCallStatus.SUCCEEDED
    assert result.attempt_count == 2
    assert calls == 2
    assert sleeps == []


async def test_retry_exhaustion_has_stable_error(session, test_settings):
    calls = 0

    async def unavailable(_payload, _context):
        nonlocal calls
        calls += 1
        raise ExternalServiceUnavailableError()

    runtime, _ = executor(
        session,
        test_settings,
        definition(
            unavailable,
            attempts=2,
            retryable=frozenset({ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE}),
        ),
    )
    result = await runtime.execute("runtime_tool", {"value": 1}, context())

    assert result.error_code == ErrorCode.TOOL_RETRY_EXHAUSTED
    assert result.attempt_count == 2
    assert calls == 2


async def test_handler_app_exception_message_is_not_reflected(session, test_settings):
    secret = "handler-secret-marker"

    async def unavailable(_payload, _context):
        raise ExternalServiceUnavailableError(f"authorization={secret} internal-path=C:\\private")

    runtime, _ = executor(session, test_settings, definition(unavailable))
    result = await runtime.execute("runtime_tool", {"value": 1}, context())
    row = await session.get(ToolCall, result.tool_call_id)

    assert result.error_code == ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE
    assert result.error_message == "External service is unavailable"
    assert secret not in result.model_dump_json()
    assert secret not in str(row.error_message)
    assert "C:\\private" not in str(row.error_message)


async def test_sync_handler_runs_through_executor(session, test_settings):
    def sync_handler(payload, _context):
        return RuntimeOutput(result=payload.value + 1)

    runtime, _ = executor(session, test_settings, definition(sync_handler))
    result = await runtime.execute("runtime_tool", {"value": 4}, context())
    assert result.data == {"result": 5, "token": None}


async def test_sync_timeout_cannot_late_overwrite_terminal_audit(session, test_settings):
    calls = 0

    def slow_sync_handler(payload, _context):
        nonlocal calls
        calls += 1
        time.sleep(0.02)
        return {"result": payload.value}

    runtime, _ = executor(
        session,
        test_settings,
        definition(slow_sync_handler, timeout=0.001),
    )
    result = await runtime.execute("runtime_tool", {"value": 1}, context())
    await asyncio.sleep(0.04)

    row = await session.get(ToolCall, result.tool_call_id)
    await session.refresh(row)
    logs = (
        await session.scalars(
            select(OperationLog).where(OperationLog.tool_call_id == result.tool_call_id)
        )
    ).all()
    assert calls == 1
    assert row.status == ToolCallStatus.TIMED_OUT
    assert row.error_code == ErrorCode.TOOL_TIMEOUT
    assert len(logs) == 1
    assert logs[0].status == "timed_out"


async def test_write_waits_for_confirmation_and_executes_exactly_once(session, test_settings):
    user, task = await create_user_and_task(session)
    calls = 0

    async def write_handler(payload, _context):
        nonlocal calls
        calls += 1
        return {"result": payload.value}

    runtime, registry = executor(
        session,
        test_settings,
        definition(write_handler, risk=ToolRiskLevel.WRITE),
    )
    request_context = context(
        user_id=user.id,
        task_id=task.id,
        idempotency_key=f"write-{uuid4()}",
    )
    initial = await runtime.execute(
        "runtime_tool",
        {"value": 7},
        request_context,
        target_type="test-record",
        target_id="7",
    )

    assert initial.status is ToolCallStatus.WAITING_CONFIRMATION
    assert initial.confirmation_required is True
    assert initial.confirmation_id is not None
    assert calls == 0
    confirmation = await session.get(ConfirmationTask, initial.confirmation_id)
    assert confirmation is not None
    assert confirmation.tool_name == "runtime_tool"
    assert confirmation.tool_input == {"value": 7, "password": None, "private_note": None}

    service = build_confirmation_service(registry, session, test_settings)
    first = await service.confirm(confirmation.id, user.id)
    second = await service.confirm(confirmation.id, user.id)

    assert first.status == ConfirmationStatus.SUCCEEDED
    assert second.status == ConfirmationStatus.SUCCEEDED
    assert calls == 1
    linked = (
        await session.scalars(select(ToolCall).where(ToolCall.confirmation_id == confirmation.id))
    ).all()
    assert linked[0].status == ToolCallStatus.SUCCEEDED
    assert linked[0].attempt_count == 1

    replay = await runtime.execute(
        "runtime_tool",
        {"value": 7},
        request_context,
        target_type="test-record",
        target_id="7",
    )
    assert replay.status is ToolCallStatus.SUCCEEDED
    assert replay.attempt_count == 0
    assert replay.confirmation_id == confirmation.id
    assert calls == 1


async def test_write_idempotency_reuses_confirmation_and_detects_conflict(session, test_settings):
    user, task = await create_user_and_task(session)

    async def handler(payload, _context):
        return {"result": payload.value}

    runtime, _ = executor(
        session,
        test_settings,
        definition(handler, risk=ToolRiskLevel.WRITE),
    )
    key = f"write-{uuid4()}"
    first = await runtime.execute(
        "runtime_tool",
        {"value": 1},
        context(user_id=user.id, task_id=task.id, idempotency_key=key),
        target_type="record",
        target_id="1",
    )
    duplicate = await runtime.execute(
        "runtime_tool",
        {"value": 1},
        context(user_id=user.id, task_id=task.id, idempotency_key=key),
        target_type="record",
        target_id="1",
    )
    conflict = await runtime.execute(
        "runtime_tool",
        {"value": 2},
        context(user_id=user.id, task_id=task.id, idempotency_key=key),
        target_type="record",
        target_id="1",
    )

    assert duplicate.confirmation_id == first.confirmation_id
    assert conflict.status is ToolCallStatus.BLOCKED
    assert conflict.error_code == ErrorCode.TOOL_IDEMPOTENCY_CONFLICT
    confirmations = (await session.scalars(select(ConfirmationTask))).all()
    assert len(confirmations) == 1


async def test_idempotency_scope_separates_user_tool_target_and_version(
    session,
    test_settings,
):
    first_user, first_task = await create_user_and_task(session)
    second_user, second_task = await create_user_and_task(session)

    async def handler(payload, _context):
        return {"result": payload.value}

    registry = ToolRegistry(test_settings)
    registry.register(definition(handler, risk=ToolRiskLevel.WRITE))
    registry.register(definition(handler, name="other_runtime_tool", risk=ToolRiskLevel.WRITE))
    runtime = ToolExecutor(registry, session, test_settings)
    key = f"scoped-{uuid4()}"
    results = [
        await runtime.execute(
            "runtime_tool",
            {"value": 1},
            context(
                user_id=first_user.id,
                task_id=first_task.id,
                idempotency_key=key,
            ),
            target_type="record",
            target_id="1",
        ),
        await runtime.execute(
            "runtime_tool",
            {"value": 1},
            context(
                user_id=second_user.id,
                task_id=second_task.id,
                idempotency_key=key,
            ),
            target_type="record",
            target_id="1",
        ),
        await runtime.execute(
            "other_runtime_tool",
            {"value": 1},
            context(
                user_id=first_user.id,
                task_id=first_task.id,
                idempotency_key=key,
            ),
            target_type="record",
            target_id="1",
        ),
        await runtime.execute(
            "runtime_tool",
            {"value": 1},
            context(
                user_id=first_user.id,
                task_id=first_task.id,
                idempotency_key=key,
            ),
            target_type="record",
            target_id="2",
        ),
    ]
    version_two_registry = ToolRegistry(test_settings)
    version_two_registry.register(
        definition(
            handler,
            version="2.0.0",
            risk=ToolRiskLevel.WRITE,
        )
    )
    results.append(
        await ToolExecutor(version_two_registry, session, test_settings).execute(
            "runtime_tool",
            {"value": 1},
            context(
                user_id=first_user.id,
                task_id=first_task.id,
                idempotency_key=key,
            ),
            target_type="record",
            target_id="1",
        )
    )

    assert len({item.confirmation_id for item in results}) == 5
    assert all(item.confirmation_required for item in results)


async def test_confirmation_secret_is_redacted_and_never_persisted(
    session,
    test_settings,
):
    user, task = await create_user_and_task(session)

    async def handler(payload, _context):
        return {"result": payload.value}

    runtime, _ = executor(
        session,
        test_settings,
        definition(handler, risk=ToolRiskLevel.WRITE),
    )
    secret = "confirmation-secret-marker"
    result = await runtime.execute(
        "runtime_tool",
        {"value": 1, "password": secret},
        context(
            user_id=user.id,
            task_id=task.id,
            idempotency_key=f"secret-{uuid4()}",
        ),
    )
    tool_call = await session.get(ToolCall, result.tool_call_id)
    confirmations = (await session.scalars(select(ConfirmationTask))).all()
    logs = (await session.scalars(select(OperationLog))).all()

    assert result.status is ToolCallStatus.BLOCKED
    assert confirmations == []
    assert tool_call.input_summary["password"] == "[REDACTED]"
    assert secret not in str(tool_call.input_summary)
    assert secret not in str(tool_call.input_digest)
    assert all(secret not in str(log.details) for log in logs)


@pytest.mark.parametrize(
    ("before_snapshot", "after_snapshot", "risk_warning"),
    [
        (None, {"value": 2}, "Dangerous"),
        ({"value": 1}, None, "Dangerous"),
        ({"value": 1}, {"value": 2}, None),
    ],
)
async def test_high_risk_requires_snapshots_and_warning(
    session,
    test_settings,
    before_snapshot,
    after_snapshot,
    risk_warning,
):
    user, task = await create_user_and_task(session)
    calls = 0

    async def handler(payload, _context):
        nonlocal calls
        calls += 1
        return {"result": payload.value}

    runtime, _ = executor(
        session,
        test_settings,
        definition(handler, risk=ToolRiskLevel.HIGH_RISK),
    )
    result = await runtime.execute(
        "runtime_tool",
        {"value": 1},
        context(
            user_id=user.id,
            task_id=task.id,
            idempotency_key=f"high-{uuid4()}",
        ),
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        risk_warning=risk_warning,
    )
    assert result.status is ToolCallStatus.BLOCKED
    assert calls == 0


async def test_high_risk_warning_is_sanitized_before_confirmation(
    session,
    test_settings,
):
    user, task = await create_user_and_task(session)

    async def handler(payload, _context):
        return {"result": payload.value}

    runtime, _ = executor(
        session,
        test_settings,
        definition(handler, risk=ToolRiskLevel.HIGH_RISK),
    )
    secret = "warning-secret-marker"
    result = await runtime.execute(
        "runtime_tool",
        {"value": 1},
        context(
            user_id=user.id,
            task_id=task.id,
            idempotency_key=f"warning-{uuid4()}",
        ),
        before_snapshot={"value": 0},
        after_snapshot={"value": 1},
        risk_warning=f"api_key={secret}",
    )
    confirmation = await session.get(ConfirmationTask, result.confirmation_id)

    assert result.confirmation_required is True
    assert confirmation.risk_warning == "api_key=[REDACTED]"
    assert secret not in str(confirmation.risk_warning)


async def test_canceled_confirmation_and_version_conflict_never_execute(session, test_settings):
    user, task = await create_user_and_task(session)
    calls = 0

    async def handler(payload, _context):
        nonlocal calls
        calls += 1
        return {"result": payload.value}

    runtime, registry = executor(
        session,
        test_settings,
        definition(handler, risk=ToolRiskLevel.WRITE),
    )
    pending = await runtime.execute(
        "runtime_tool",
        {"value": 1},
        context(
            user_id=user.id,
            task_id=task.id,
            idempotency_key=f"cancel-{uuid4()}",
        ),
    )
    service = build_confirmation_service(registry, session, test_settings)
    await service.cancel(pending.confirmation_id)
    with pytest.raises(Exception, match="Canceled confirmation"):
        await service.confirm(pending.confirmation_id, user.id)
    assert calls == 0

    other = await runtime.execute(
        "runtime_tool",
        {"value": 2},
        context(
            user_id=user.id,
            task_id=task.id,
            idempotency_key=f"version-{uuid4()}",
        ),
    )
    confirmation = await session.get(ConfirmationTask, other.confirmation_id)
    confirmation.tool_version = "2.0.0"
    failed = await service.confirm(other.confirmation_id, user.id)
    assert failed.status == ConfirmationStatus.FAILED
    assert failed.error_message == "Confirmation execution failed"
    assert calls == 0


async def test_mcp_write_tool_cannot_bypass_confirmation(session, test_settings):
    user, task = await create_user_and_task(session)
    calls = 0

    async def handler(payload, _context):
        nonlocal calls
        calls += 1
        return {"result": payload.value}

    runtime, _ = executor(
        session,
        test_settings,
        definition(
            handler,
            risk=ToolRiskLevel.WRITE,
            expose_to_mcp=True,
        ),
    )
    result = await runtime.execute(
        "runtime_tool",
        {"value": 1},
        context(
            user_id=user.id,
            task_id=task.id,
            caller_type=ToolCallerType.MCP,
            idempotency_key=f"mcp-{uuid4()}",
        ),
    )
    assert result.confirmation_required is True
    assert calls == 0


def test_recursive_redaction_is_non_mutating_and_supports_extra_fields(test_settings):
    source = {
        "password": "one",
        "API_KEY": "upper-case-secret",
        "token_count": 17,
        "nested": {"access_token": "two", "private_note": "three"},
        "items": [{"secret": "four"}, ("safe", {"cookie": "five"})],
    }
    original = deepcopy(source)
    redacted = redact_nested(source, extra_sensitive_fields={"private_note"})

    assert redacted["password"] == "[REDACTED]"
    assert redacted["API_KEY"] == "[REDACTED]"
    assert redacted["token_count"] == 17
    assert redacted["nested"]["access_token"] == "[REDACTED]"
    assert redacted["nested"]["private_note"] == "[REDACTED]"
    assert redacted["items"][0]["secret"] == "[REDACTED]"
    assert redacted["items"][1][1]["cookie"] == "[REDACTED]"
    assert source == original

    summary = audit_summary(
        {"safe": "x" * 5000},
        max_bytes=1024,
    )
    assert summary["truncated"] is True
    assert summary["original_size_bytes"] > 1024


def test_input_digest_is_stable_for_json_key_order():
    async def handler(_payload, _context):
        return {"result": 1}

    tool = definition(handler)
    first = {"outer": {"a": 1, "b": 2}, "items": [{"x": 1, "y": 2}]}
    second = {"items": [{"y": 2, "x": 1}], "outer": {"b": 2, "a": 1}}

    assert ToolExecutor._input_digest(
        tool,
        first,
        user_id=None,
        target_type="fixture",
        target_id="1",
    ) == ToolExecutor._input_digest(
        tool,
        second,
        user_id=None,
        target_type="fixture",
        target_id="1",
    )


def test_execution_context_rejects_secret_metadata():
    with pytest.raises(ValidationError, match="sensitive fields"):
        ToolExecutionContext(
            request_id=str(uuid4()),
            caller_type=ToolCallerType.TEST,
            caller_name="pytest",
            metadata={"access_token": "not-allowed"},
        )
