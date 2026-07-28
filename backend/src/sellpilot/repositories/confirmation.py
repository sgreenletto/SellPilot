from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def claim_for_execution(
        self,
        confirmation_id: UUID,
        *,
        confirmed_by: UUID,
        confirmed_at: datetime,
        execution_started_at: datetime,
    ) -> ConfirmationTask | None:
        """Atomically claim pending/confirmed work across SQLite and PostgreSQL."""

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

    async def list(self, page: int, page_size: int) -> tuple[list[ConfirmationTask], int]:
        total = await self.session.scalar(select(func.count()).select_from(ConfirmationTask))
        result = await self.session.execute(
            select(ConfirmationTask)
            .order_by(ConfirmationTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)
