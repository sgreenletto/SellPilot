from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.enums import OperationStatus
from sellpilot.db.models.operation_log import OperationLog


class OperationLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, operation_log: OperationLog) -> OperationLog:
        self.session.add(operation_log)
        await self.session.flush()
        return operation_log

    async def list_by_task(
        self,
        task_id: UUID,
        *,
        page: int,
        page_size: int,
        event_type: str | None = None,
        status: OperationStatus | None = None,
    ) -> tuple[list[OperationLog], int]:
        filters = [OperationLog.agent_task_id == task_id]
        if event_type is not None:
            filters.append(OperationLog.action == event_type)
        if status is not None:
            filters.append(func.lower(OperationLog.status) == status.value)
        total = await self.session.scalar(
            select(func.count()).select_from(OperationLog).where(*filters)
        )
        result = await self.session.execute(
            select(OperationLog)
            .where(*filters)
            .order_by(OperationLog.created_at.asc(), OperationLog.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)
