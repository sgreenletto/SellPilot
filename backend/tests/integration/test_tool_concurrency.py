import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import func, select

from sellpilot.core.enums import ConfirmationStatus, ToolCallerType, ToolRiskLevel
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.db.models.tool_call import ToolCall
from sellpilot.db.models.user import User
from sellpilot.repositories.confirmation import ConfirmationRepository
from sellpilot.services.task import TaskService
from sellpilot.tools.contracts import (
    RetryPolicy,
    ToolDefinition,
    ToolExecutionContext,
)
from sellpilot.tools.executor import ToolExecutor
from sellpilot.tools.registry import ToolRegistry
from sellpilot.tools.runtime import build_confirmation_service


class ConcurrentInput(BaseModel):
    value: int


class ConcurrentOutput(BaseModel):
    result: int


def build_registry(test_settings, handler):
    registry = ToolRegistry(test_settings)
    registry.register(
        ToolDefinition(
            name="concurrent_write",
            version="1.0.0",
            description="Test-only concurrent write",
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
            handler=handler,
        )
    )
    return registry


async def test_concurrent_duplicate_confirmation_executes_handler_once(
    session_factory,
    test_settings,
):
    calls = 0

    async def handler(payload, _context):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return {"result": payload.value}

    registry = build_registry(test_settings, handler)

    async with session_factory() as session:
        user = User(
            username=f"concurrent-{uuid4()}",
            password_hash="test-hash",
            role="ADMIN",
        )
        session.add(user)
        await session.flush()
        task = await TaskService(session).create_internal_task(
            task_type="diagnostic",
            user_input="concurrent confirmation",
            created_by=user.id,
        )
        result = await ToolExecutor(registry, session, test_settings).execute(
            "concurrent_write",
            {"value": 1},
            ToolExecutionContext(
                request_id=str(uuid4()),
                user_id=user.id,
                task_id=task.id,
                idempotency_key=f"concurrent-{uuid4()}",
                caller_type=ToolCallerType.TEST,
                caller_name="pytest",
            ),
        )
        await session.commit()
        confirmation_id = result.confirmation_id
        user_id = user.id

    async def confirm_once():
        async with session_factory() as session:
            confirmation = await build_confirmation_service(
                registry,
                session,
                test_settings,
            ).confirm(confirmation_id, user_id)
            await session.commit()
            return ConfirmationStatus(confirmation.status)

    statuses = await asyncio.gather(confirm_once(), confirm_once())

    assert calls == 1
    assert ConfirmationStatus.SUCCEEDED in statuses
    assert set(statuses) <= {
        ConfirmationStatus.EXECUTING,
        ConfirmationStatus.SUCCEEDED,
    }

    async with session_factory() as session:
        confirmation = await session.get(ConfirmationTask, confirmation_id)
        assert confirmation is not None
        assert confirmation.status == ConfirmationStatus.SUCCEEDED


class SimulatedProcessCrash(BaseException):
    """Represent a hard process interruption outside normal exception handling."""


@pytest.mark.asyncio
async def test_crash_after_claim_leaves_detectable_stale_execution(
    session_factory,
    test_settings,
):
    async def crash_handler(_payload, _context):
        raise SimulatedProcessCrash

    registry = build_registry(test_settings, crash_handler)

    async with session_factory() as session:
        user = User(
            username=f"crash-{uuid4()}",
            password_hash="test-hash",
            role="ADMIN",
        )
        session.add(user)
        await session.flush()
        task = await TaskService(session).create_internal_task(
            task_type="diagnostic",
            user_input="crash recovery marker",
            created_by=user.id,
        )
        result = await ToolExecutor(registry, session, test_settings).execute(
            "concurrent_write",
            {"value": 1},
            ToolExecutionContext(
                request_id=str(uuid4()),
                user_id=user.id,
                task_id=task.id,
                idempotency_key=f"crash-{uuid4()}",
                caller_type=ToolCallerType.TEST,
                caller_name="pytest",
            ),
            target_type="test-record",
            target_id="crash-target",
        )
        await session.commit()
        confirmation_id = result.confirmation_id
        user_id = user.id

    async with session_factory() as session:
        with pytest.raises(SimulatedProcessCrash):
            await build_confirmation_service(
                registry,
                session,
                test_settings,
            ).confirm(confirmation_id, user_id)

    async with session_factory() as session:
        confirmation = await session.get(ConfirmationTask, confirmation_id)
        assert confirmation is not None
        assert confirmation.status == ConfirmationStatus.EXECUTING
        assert confirmation.execution_started_at is not None

        tool_call = await session.scalar(
            select(ToolCall).where(ToolCall.confirmation_id == confirmation_id)
        )
        assert tool_call is not None
        assert tool_call.status == "running"

        stale = await ConfirmationRepository(session).list_stale_executing(
            started_before=datetime.now(UTC) + timedelta(seconds=1)
        )
        assert [item.id for item in stale] == [confirmation_id]


async def test_concurrent_same_idempotency_key_creates_one_confirmation(
    session_factory,
    test_settings,
):
    async def handler(payload, _context):
        return {"result": payload.value}

    registry = build_registry(test_settings, handler)
    async with session_factory() as session:
        user = User(
            username=f"idempotency-{uuid4()}",
            password_hash="test-hash",
            role="ADMIN",
        )
        session.add(user)
        await session.flush()
        task = await TaskService(session).create_internal_task(
            task_type="diagnostic",
            user_input="concurrent idempotency",
            created_by=user.id,
        )
        await session.commit()
        user_id = user.id
        task_id = task.id

    key = f"same-key-{uuid4()}"

    async def request_confirmation():
        async with session_factory() as session:
            result = await ToolExecutor(registry, session, test_settings).execute(
                "concurrent_write",
                {"value": 1},
                ToolExecutionContext(
                    request_id=str(uuid4()),
                    user_id=user_id,
                    task_id=task_id,
                    idempotency_key=key,
                    caller_type=ToolCallerType.TEST,
                    caller_name="pytest",
                ),
                target_type="test-record",
                target_id="1",
            )
            await session.commit()
            return result.confirmation_id

    confirmation_ids = await asyncio.gather(
        request_confirmation(),
        request_confirmation(),
    )

    assert confirmation_ids[0] == confirmation_ids[1]
    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(ConfirmationTask))
        assert count == 1
