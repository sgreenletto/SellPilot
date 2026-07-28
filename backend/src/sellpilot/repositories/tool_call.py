from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.enums import ToolCallStatus, ToolRiskLevel
from sellpilot.db.models.tool_call import ToolCall


class ToolCallRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, tool_call: ToolCall) -> ToolCall:
        self.session.add(tool_call)
        await self.session.flush()
        return tool_call

    async def get(self, tool_call_id: UUID) -> ToolCall | None:
        return await self.session.get(ToolCall, tool_call_id)

    async def get_for_update(self, tool_call_id: UUID) -> ToolCall | None:
        result = await self.session.execute(
            select(ToolCall).where(ToolCall.id == tool_call_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def list_by_confirmation(self, confirmation_id: UUID) -> list[ToolCall]:
        result = await self.session.execute(
            select(ToolCall)
            .where(ToolCall.confirmation_id == confirmation_id)
            .order_by(ToolCall.created_at.asc(), ToolCall.id.asc())
        )
        return list(result.scalars())

    async def get_succeeded_by_confirmation(self, confirmation_id: UUID) -> ToolCall | None:
        result = await self.session.execute(
            select(ToolCall)
            .where(
                ToolCall.confirmation_id == confirmation_id,
                ToolCall.status == ToolCallStatus.SUCCEEDED,
            )
            .order_by(ToolCall.completed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _apply_filters(
        statement: Select[tuple[ToolCall]],
        *,
        tool_name: str | None,
        status: ToolCallStatus | None,
        risk_level: ToolRiskLevel | None,
        task_id: UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> Select[tuple[ToolCall]]:
        if tool_name is not None:
            statement = statement.where(ToolCall.tool_name == tool_name)
        if status is not None:
            statement = statement.where(ToolCall.status == status)
        if risk_level is not None:
            statement = statement.where(ToolCall.risk_level == risk_level)
        if task_id is not None:
            statement = statement.where(ToolCall.task_id == task_id)
        if created_from is not None:
            statement = statement.where(ToolCall.created_at >= created_from)
        if created_to is not None:
            statement = statement.where(ToolCall.created_at <= created_to)
        return statement

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        tool_name: str | None = None,
        status: ToolCallStatus | None = None,
        risk_level: ToolRiskLevel | None = None,
        task_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[ToolCall], int]:
        query = self._apply_filters(
            select(ToolCall),
            tool_name=tool_name,
            status=status,
            risk_level=risk_level,
            task_id=task_id,
            created_from=created_from,
            created_to=created_to,
        )
        count_query = self._apply_filters(
            select(ToolCall),
            tool_name=tool_name,
            status=status,
            risk_level=risk_level,
            task_id=task_id,
            created_from=created_from,
            created_to=created_to,
        ).with_only_columns(func.count())
        total = await self.session.scalar(count_query)
        result = await self.session.execute(
            query.order_by(ToolCall.created_at.desc(), ToolCall.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)
