from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.enums import (
    CONFIRMATION_TRANSITIONS,
    ConfirmationStatus,
    RiskLevel,
)
from sellpilot.core.exceptions import (
    ConfirmationExecutorNotFoundError,
    ResourceNotFoundError,
    StateConflictError,
)
from sellpilot.core.logging import redact_sensitive
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.repositories.confirmation import ConfirmationRepository

ConfirmationExecutor = Callable[[ConfirmationTask], Awaitable[dict[str, Any]]]


class ConfirmationService:
    def __init__(self, session: AsyncSession) -> None:
        self.confirmations = ConfirmationRepository(session)
        self._executors: dict[str, ConfirmationExecutor] = {}

    def register_executor(self, operation_type: str, executor: ConfirmationExecutor) -> None:
        if operation_type in self._executors:
            raise StateConflictError(
                f"Executor already registered for operation type '{operation_type}'"
            )
        self._executors[operation_type] = executor

    async def create(
        self,
        *,
        agent_task_id: UUID,
        operation_type: str,
        target_type: str,
        target_id: str | None,
        risk_level: RiskLevel,
        idempotency_key: str,
        created_by: UUID,
        before_snapshot: dict[str, Any] | None = None,
        after_snapshot: dict[str, Any] | None = None,
    ) -> ConfirmationTask:
        existing = await self.confirmations.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        return await self.confirmations.add(
            ConfirmationTask(
                agent_task_id=agent_task_id,
                operation_type=operation_type,
                target_type=target_type,
                target_id=target_id,
                risk_level=risk_level,
                idempotency_key=idempotency_key,
                created_by=created_by,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
                status=ConfirmationStatus.PENDING,
            )
        )

    async def get(self, confirmation_id: UUID) -> ConfirmationTask:
        confirmation = await self.confirmations.get(confirmation_id)
        if confirmation is None:
            raise ResourceNotFoundError("Confirmation task not found")
        return confirmation

    async def list(self, page: int, page_size: int) -> tuple[list[ConfirmationTask], int]:
        return await self.confirmations.list(page, page_size)

    def _transition(self, confirmation: ConfirmationTask, target: ConfirmationStatus) -> None:
        current = ConfirmationStatus(confirmation.status)
        if target not in CONFIRMATION_TRANSITIONS[current]:
            raise StateConflictError(f"Confirmation cannot transition from {current} to {target}")
        confirmation.status = target

    async def cancel(self, confirmation_id: UUID) -> ConfirmationTask:
        confirmation = await self.get(confirmation_id)
        self._transition(confirmation, ConfirmationStatus.CANCELED)
        return confirmation

    async def confirm(self, confirmation_id: UUID, confirmed_by: UUID) -> ConfirmationTask:
        confirmation = await self.confirmations.get_for_update(confirmation_id)
        if confirmation is None:
            raise ResourceNotFoundError("Confirmation task not found")
        current = ConfirmationStatus(confirmation.status)
        if current in {
            ConfirmationStatus.CONFIRMED,
            ConfirmationStatus.EXECUTING,
            ConfirmationStatus.SUCCEEDED,
            ConfirmationStatus.FAILED,
        }:
            return confirmation
        if current is ConfirmationStatus.CANCELED:
            raise StateConflictError("Canceled confirmation cannot be confirmed")

        executor = self._executors.get(confirmation.operation_type)
        if executor is None:
            raise ConfirmationExecutorNotFoundError(confirmation.operation_type)

        self._transition(confirmation, ConfirmationStatus.CONFIRMED)
        confirmation.confirmed_by = confirmed_by
        confirmation.confirmed_at = datetime.now(UTC)
        self._transition(confirmation, ConfirmationStatus.EXECUTING)
        try:
            confirmation.execution_result = await executor(confirmation)
            confirmation.executed_at = datetime.now(UTC)
            self._transition(confirmation, ConfirmationStatus.SUCCEEDED)
        except Exception as exc:
            confirmation.error_message = redact_sensitive(exc)[:1000]
            confirmation.executed_at = datetime.now(UTC)
            self._transition(confirmation, ConfirmationStatus.FAILED)
        return confirmation
