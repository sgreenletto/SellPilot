from uuid import UUID

from sqlalchemy import func, select
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

    async def get_by_idempotency_key(self, key: str) -> ConfirmationTask | None:
        result = await self.session.execute(
            select(ConfirmationTask).where(ConfirmationTask.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def list(self, page: int, page_size: int) -> tuple[list[ConfirmationTask], int]:
        total = await self.session.scalar(select(func.count()).select_from(ConfirmationTask))
        result = await self.session.execute(
            select(ConfirmationTask)
            .order_by(ConfirmationTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)
