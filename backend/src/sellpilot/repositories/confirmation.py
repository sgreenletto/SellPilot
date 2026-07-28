from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.enums import ConfirmationStatus
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.confirmation_task import ConfirmationTask


class ConfirmationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, confirmation: ConfirmationTask) -> ConfirmationTask:
        self.session.add(confirmation)
        await self.session.flush()
        return confirmation

    async def get(self, confirmation_id: UUID) -> ConfirmationTask | None:
        return await self.session.get(ConfirmationTask, confirmation_id)

    async def get_for_update(self, confirmation_id: UUID) -> ConfirmationTask | None:
        result = await self.session.execute(
            select(ConfirmationTask).where(ConfirmationTask.id == confirmation_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_owned(
        self,
        confirmation_id: UUID,
        user_id: UUID,
    ) -> ConfirmationTask | None:
        result = await self.session.execute(
            select(ConfirmationTask)
            .join(AgentTask, AgentTask.id == ConfirmationTask.agent_task_id)
            .where(
                ConfirmationTask.id == confirmation_id,
                ConfirmationTask.created_by == user_id,
                AgentTask.created_by == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def claim_for_execution(
        self,
        confirmation_id: UUID,
        *,
        confirmed_by: UUID,
        confirmed_at: datetime,
        execution_started_at: datetime,
    ) -> ConfirmationTask | None:
        """Atomically claim pending or confirmed work in PostgreSQL."""

        result = await self.session.execute(
            update(ConfirmationTask)
            .where(
                ConfirmationTask.id == confirmation_id,
                func.lower(ConfirmationTask.status).in_({"pending", "confirmed"}),
            )
            .values(
                status="executing",
                confirmed_by=confirmed_by,
                confirmed_at=confirmed_at,
                execution_started_at=execution_started_at,
            )
        )
        if result.rowcount != 1:
            return None
        confirmation = await self.get(confirmation_id)
        if confirmation is not None:
            await self.session.refresh(confirmation)
        return confirmation

    async def get_by_idempotency_scope(self, scope: str) -> ConfirmationTask | None:
        result = await self.session.execute(
            select(ConfirmationTask).where(ConfirmationTask.idempotency_scope == scope)
        )
        return result.scalar_one_or_none()

    async def list_stale_executing(
        self,
        *,
        started_before: datetime,
        limit: int = 100,
    ) -> list[ConfirmationTask]:
        result = await self.session.execute(
            select(ConfirmationTask)
            .where(
                func.lower(ConfirmationTask.status) == "executing",
                ConfirmationTask.execution_started_at <= started_before,
            )
            .order_by(ConfirmationTask.execution_started_at.asc())
            .limit(limit)
        )
        return list(result.scalars())

    async def list_by_task(self, task_id: UUID) -> list[ConfirmationTask]:
        result = await self.session.execute(
            select(ConfirmationTask)
            .where(ConfirmationTask.agent_task_id == task_id)
            .order_by(ConfirmationTask.created_at.asc(), ConfirmationTask.id.asc())
        )
        return list(result.scalars())

    async def list_owned(
        self,
        page: int,
        page_size: int,
        *,
        user_id: UUID,
        task_id: UUID | None = None,
        status: ConfirmationStatus | None = None,
    ) -> tuple[list[ConfirmationTask], int]:
        filters = [
            ConfirmationTask.created_by == user_id,
            AgentTask.created_by == user_id,
        ]
        if task_id is not None:
            filters.append(ConfirmationTask.agent_task_id == task_id)
        if status is not None:
            filters.append(func.lower(ConfirmationTask.status) == status.value)
        total = await self.session.scalar(
            select(func.count())
            .select_from(ConfirmationTask)
            .join(AgentTask, AgentTask.id == ConfirmationTask.agent_task_id)
            .where(*filters)
        )
        result = await self.session.execute(
            select(ConfirmationTask)
            .join(AgentTask, AgentTask.id == ConfirmationTask.agent_task_id)
            .where(*filters)
            .order_by(ConfirmationTask.created_at.desc(), ConfirmationTask.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)

    async def cancel_owned(
        self,
        confirmation_id: UUID,
        *,
        user_id: UUID,
    ) -> ConfirmationTask | None:
        owned = (
            select(ConfirmationTask.id)
            .join(
                AgentTask,
                AgentTask.id == ConfirmationTask.agent_task_id,
            )
            .where(
                ConfirmationTask.id == confirmation_id,
                ConfirmationTask.created_by == user_id,
                AgentTask.created_by == user_id,
            )
        )
        result = await self.session.execute(
            update(ConfirmationTask)
            .where(
                ConfirmationTask.id.in_(owned),
                func.lower(ConfirmationTask.status) == ConfirmationStatus.PENDING.value,
            )
            .values(status=ConfirmationStatus.CANCELED.value)
        )
        if result.rowcount != 1:
            return None
        confirmation = await self.get(confirmation_id)
        if confirmation is not None:
            await self.session.refresh(confirmation)
        return confirmation
