from uuid import uuid4

import pytest

from sellpilot.core.enums import ConfirmationStatus, TaskStatus, ToolRiskLevel
from sellpilot.core.exceptions import (
    ConfirmationExecutorNotFoundError,
    DuplicateOperationError,
    ParameterError,
    StateConflictError,
)
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.db.models.user import User
from sellpilot.services.auth import AuthService
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.services.task import TaskService


async def create_user(session, username: str = "service-admin") -> User:
    user = User(username=username, password_hash="test-hash", role="ADMIN")
    session.add(user)
    await session.flush()
    return user


async def test_task_state_transitions(session):
    user = await create_user(session)
    service = TaskService(session)
    task = await service.create_internal_task(
        task_type="diagnostic", user_input="test", created_by=user.id
    )
    assert task.status == TaskStatus.PENDING
    await service.start(task.id)
    await service.update_current_step(task.id, "validate")
    await service.complete(task.id, {"ok": True})
    assert task.status == TaskStatus.SUCCEEDED
    assert task.result == {"ok": True}
    with pytest.raises(StateConflictError):
        await service.fail(task.id, "LATE_FAILURE", "too late")


async def test_task_rejects_illegal_transition(session):
    user = await create_user(session)
    service = TaskService(session)
    task = await service.create_internal_task(
        task_type="diagnostic", user_input="test", created_by=user.id
    )
    with pytest.raises(StateConflictError):
        await service.complete(task.id, {"ok": True})


async def test_legacy_uppercase_task_status_round_trips_through_string_column(session):
    user = await create_user(session, username="legacy-task-admin")
    task = AgentTask(
        task_type="diagnostic",
        user_input="legacy row",
        status="PENDING",
        created_by=user.id,
    )
    session.add(task)
    await session.flush()
    task_id = task.id
    session.expire(task)

    started = await TaskService(session).start(task_id)

    assert started.status == TaskStatus.RUNNING


@pytest.mark.parametrize("start_first", [False, True])
async def test_task_can_fail_from_pending_or_running(session, start_first):
    user = await create_user(session, username=f"failure-admin-{start_first}")
    service = TaskService(session)
    task = await service.create_internal_task(
        task_type="diagnostic", user_input="test", created_by=user.id
    )
    if start_first:
        await service.start(task.id)
    await service.fail(task.id, "EXPECTED_FAILURE", "test failure")
    assert task.status == TaskStatus.FAILED
    with pytest.raises(StateConflictError):
        await service.start(task.id)


async def confirmation_fixture(session):
    user = await create_user(session)
    task = await TaskService(session).create_internal_task(
        task_type="diagnostic", user_input="test", created_by=user.id
    )
    service = ConfirmationService(session)
    confirmation = await service.create(
        agent_task_id=task.id,
        operation_type="test.write",
        target_type="test-target",
        target_id="target-1",
        risk_level=ToolRiskLevel.WRITE,
        idempotency_key=str(uuid4()),
        created_by=user.id,
    )
    return service, confirmation, user


async def test_confirmation_cancel_only_from_pending(session):
    service, confirmation, _ = await confirmation_fixture(session)
    await service.cancel(confirmation.id)
    assert confirmation.status == ConfirmationStatus.CANCELED
    with pytest.raises(StateConflictError):
        await service.cancel(confirmation.id)


async def test_confirmation_without_executor_remains_pending(session):
    service, confirmation, user = await confirmation_fixture(session)
    with pytest.raises(ConfirmationExecutorNotFoundError):
        await service.confirm(confirmation.id, user.id)
    assert confirmation.status == ConfirmationStatus.PENDING


async def test_legacy_uppercase_confirmation_status_executes_once(session):
    user = await create_user(session, username="legacy-confirmation-admin")
    task = await TaskService(session).create_internal_task(
        task_type="diagnostic", user_input="legacy row", created_by=user.id
    )
    confirmation = ConfirmationTask(
        agent_task_id=task.id,
        operation_type="test.legacy-write",
        target_type="test-target",
        target_id="target-1",
        risk_level="WRITE",
        idempotency_key=str(uuid4()),
        created_by=user.id,
        status="PENDING",
    )
    session.add(confirmation)
    await session.flush()
    confirmation_id = confirmation.id
    user_id = user.id
    session.expire(confirmation)

    calls = 0

    async def executor(_):
        nonlocal calls
        calls += 1
        return {"executed": True}

    service = ConfirmationService(session)
    service.register_executor("test.legacy-write", executor)
    first = await service.confirm(confirmation_id, user_id)
    second = await service.confirm(confirmation_id, user_id)

    assert first.status == ConfirmationStatus.SUCCEEDED
    assert second.status == ConfirmationStatus.SUCCEEDED
    assert first.risk_level == "WRITE"
    assert calls == 1


async def test_confirmation_confirm_is_idempotent(session):
    service, confirmation, user = await confirmation_fixture(session)
    calls = 0

    async def executor(_):
        nonlocal calls
        calls += 1
        return {"executed": True}

    service.register_executor("test.write", executor)
    first = await service.confirm(confirmation.id, user.id)
    second = await service.confirm(confirmation.id, user.id)
    assert first is second
    assert first.status == ConfirmationStatus.SUCCEEDED
    assert first.execution_result == {"executed": True}
    assert calls == 1


async def test_confirmation_executor_failure_is_saved_and_idempotent(session):
    service, confirmation, user = await confirmation_fixture(session)
    calls = 0

    async def failing_executor(_):
        nonlocal calls
        calls += 1
        raise RuntimeError("expected executor failure")

    service.register_executor("test.write", failing_executor)
    first = await service.confirm(confirmation.id, user.id)
    second = await service.confirm(confirmation.id, user.id)
    assert first is second
    assert first.status == ConfirmationStatus.FAILED
    assert first.error_message == "expected executor failure"
    assert calls == 1


async def test_confirmation_creation_uses_idempotency_key(session):
    user = await create_user(session)
    task = await TaskService(session).create_internal_task(
        task_type="diagnostic", user_input="test", created_by=user.id
    )
    service = ConfirmationService(session)
    key = str(uuid4())
    values = dict(
        agent_task_id=task.id,
        operation_type="test.write",
        target_type="test-target",
        target_id=None,
        risk_level=ToolRiskLevel.WRITE,
        idempotency_key=key,
        created_by=user.id,
    )
    first = await service.create(**values)
    second = await service.create(**values)
    assert first.id == second.id


async def test_high_risk_confirmation_requires_full_snapshots(session):
    user = await create_user(session)
    task = await TaskService(session).create_internal_task(
        task_type="diagnostic", user_input="test", created_by=user.id
    )
    service = ConfirmationService(session)
    with pytest.raises(ParameterError, match="before and after snapshots"):
        await service.create(
            agent_task_id=task.id,
            operation_type="test.high-risk",
            target_type="test-target",
            target_id="target-1",
            risk_level=ToolRiskLevel.HIGH_RISK,
            idempotency_key=str(uuid4()),
            created_by=user.id,
            before_snapshot={"state": "before"},
        )


async def test_read_operation_cannot_create_confirmation(session):
    user = await create_user(session, username="read-confirmation-admin")
    task = await TaskService(session).create_internal_task(
        task_type="diagnostic", user_input="test", created_by=user.id
    )
    service = ConfirmationService(session)

    with pytest.raises(ParameterError, match="do not require"):
        await service.create(
            agent_task_id=task.id,
            operation_type="test.read",
            target_type="test-target",
            target_id="target-1",
            risk_level=ToolRiskLevel.READ,
            idempotency_key=str(uuid4()),
            created_by=user.id,
        )


async def test_duplicate_admin_username_is_explicit(session, test_settings):
    service = AuthService(session, test_settings)
    await service.create_admin("unique-admin", "A-secure-admin-password!")
    with pytest.raises(DuplicateOperationError, match="already exists"):
        await service.create_admin("unique-admin", "Another-secure-password!")
