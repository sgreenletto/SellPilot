import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.enums import (
    ConfirmationStatus,
    ToolRiskLevel,
)
from sellpilot.core.exceptions import (
    ConfirmationExecutorNotFoundError,
    ParameterError,
    ResourceNotFoundError,
    StateConflictError,
    ToolIdempotencyConflictError,
)
from sellpilot.core.logging import redact_sensitive
from sellpilot.core.transitions import validate_confirmation_transition
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.repositories.confirmation import ConfirmationRepository

ConfirmationExecutor = Callable[[ConfirmationTask], Awaitable[dict[str, Any]]]
logger = logging.getLogger(__name__)


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
        risk_level: ToolRiskLevel,
        idempotency_key: str,
        created_by: UUID,
        before_snapshot: dict[str, Any] | None = None,
        after_snapshot: dict[str, Any] | None = None,
        tool_name: str | None = None,
        tool_version: str | None = None,
        tool_input: dict[str, Any] | None = None,
        input_digest: str | None = None,
        request_id: str | None = None,
        risk_warning: str | None = None,
    ) -> ConfirmationTask:
        if risk_level is ToolRiskLevel.READ:
            raise ParameterError("Read operations do not require a confirmation task")
        if risk_level is ToolRiskLevel.HIGH_RISK and (
            before_snapshot is None or after_snapshot is None
        ):
            raise ParameterError(
                "High-risk confirmations require complete before and after snapshots"
            )
        idempotency_scope = self.build_idempotency_scope(
            created_by=created_by,
            operation_type=operation_type,
            tool_name=tool_name,
            tool_version=tool_version,
            target_type=target_type,
            target_id=target_id,
            idempotency_key=idempotency_key,
        )
        existing = await self.confirmations.get_by_idempotency_scope(idempotency_scope)
        if existing is not None:
            self._validate_idempotent_match(
                existing,
                operation_type=operation_type,
                target_type=target_type,
                target_id=target_id,
                created_by=created_by,
                tool_name=tool_name,
                tool_version=tool_version,
                input_digest=input_digest,
            )
            return existing
        confirmation = ConfirmationTask(
            agent_task_id=agent_task_id,
            operation_type=operation_type,
            target_type=target_type,
            target_id=target_id,
            risk_level=risk_level,
            idempotency_key=idempotency_key,
            idempotency_scope=idempotency_scope,
            created_by=created_by,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            tool_name=tool_name,
            tool_version=tool_version,
            tool_input=tool_input,
            input_digest=input_digest,
            request_id=request_id,
            risk_warning=risk_warning,
            status=ConfirmationStatus.PENDING,
        )
        try:
            async with self.confirmations.session.begin_nested():
                return await self.confirmations.add(confirmation)
        except IntegrityError:
            existing = await self.confirmations.get_by_idempotency_scope(idempotency_scope)
            if existing is None:
                raise
            self._validate_idempotent_match(
                existing,
                operation_type=operation_type,
                target_type=target_type,
                target_id=target_id,
                created_by=created_by,
                tool_name=tool_name,
                tool_version=tool_version,
                input_digest=input_digest,
            )
            return existing

    @staticmethod
    def build_idempotency_scope(
        *,
        created_by: UUID,
        operation_type: str,
        tool_name: str | None,
        tool_version: str | None,
        target_type: str,
        target_id: str | None,
        idempotency_key: str,
    ) -> str:
        canonical = json.dumps(
            {
                "created_by": str(created_by),
                "operation_type": operation_type,
                "tool_name": tool_name,
                "tool_version": tool_version,
                "target_type": target_type,
                "target_id": target_id,
                "idempotency_key": idempotency_key,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_idempotent_match(
        existing: ConfirmationTask,
        *,
        operation_type: str,
        target_type: str,
        target_id: str | None,
        created_by: UUID,
        tool_name: str | None,
        tool_version: str | None,
        input_digest: str | None,
    ) -> None:
        if (
            existing.operation_type != operation_type
            or existing.target_type != target_type
            or existing.target_id != target_id
            or existing.created_by != created_by
            or existing.tool_name != tool_name
            or existing.tool_version != tool_version
            or existing.input_digest != input_digest
        ):
            if tool_name is not None:
                raise ToolIdempotencyConflictError()
            raise StateConflictError(
                "Idempotency key is already associated with another confirmation"
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
        validate_confirmation_transition(current, target)
        confirmation.status = target

    async def cancel(self, confirmation_id: UUID) -> ConfirmationTask:
        confirmation = await self.get(confirmation_id)
        self._transition(confirmation, ConfirmationStatus.CANCELED)
        return confirmation

    async def confirm(self, confirmation_id: UUID, confirmed_by: UUID) -> ConfirmationTask:
        confirmation = await self.confirmations.get(confirmation_id)
        if confirmation is None:
            raise ResourceNotFoundError("Confirmation task not found")
        current = ConfirmationStatus(confirmation.status)
        if current in {
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

        if current is ConfirmationStatus.PENDING:
            validate_confirmation_transition(
                ConfirmationStatus.PENDING,
                ConfirmationStatus.CONFIRMED,
            )
        validate_confirmation_transition(
            ConfirmationStatus.CONFIRMED,
            ConfirmationStatus.EXECUTING,
        )
        now = datetime.now(UTC)
        confirmation = await self.confirmations.claim_for_execution(
            confirmation_id,
            confirmed_by=confirmed_by,
            confirmed_at=confirmation.confirmed_at or now,
            execution_started_at=now,
        )
        if confirmation is None:
            confirmation = await self.get(confirmation_id)
            await self.confirmations.session.refresh(confirmation)
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
            raise StateConflictError("Confirmation could not be claimed for execution")
        await self.confirmations.session.commit()
        try:
            confirmation.execution_result = await executor(confirmation)
            confirmation.executed_at = datetime.now(UTC)
            self._transition(confirmation, ConfirmationStatus.SUCCEEDED)
        except Exception as exc:
            logger.error(
                "Confirmation executor failed confirmation_id=%s error=%s",
                confirmation.id,
                redact_sensitive(exc)[:1000],
            )
            confirmation.error_message = "Confirmation execution failed"
            confirmation.executed_at = datetime.now(UTC)
            self._transition(confirmation, ConfirmationStatus.FAILED)
        return confirmation
