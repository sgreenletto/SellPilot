from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.operation_log import OperationLog


class OperationLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, operation_log: OperationLog) -> OperationLog:
        self.session.add(operation_log)
        await self.session.flush()
        return operation_log
