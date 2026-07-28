from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.agent_task_step import AgentTaskStep


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, task: AgentTask) -> AgentTask:
        self.session.add(task)
        await self.session.flush()
        return task

    async def get(self, task_id: UUID) -> AgentTask | None:
        return await self.session.get(AgentTask, task_id)

    async def list(self, page: int, page_size: int) -> tuple[list[AgentTask], int]:
        total = await self.session.scalar(select(func.count()).select_from(AgentTask))
        result = await self.session.execute(
            select(AgentTask)
            .order_by(AgentTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)

    async def add_steps(self, steps: list[AgentTaskStep]) -> list[AgentTaskStep]:
        self.session.add_all(steps)
        await self.session.flush()
        return steps

    async def get_step(self, step_id: UUID) -> AgentTaskStep | None:
        return await self.session.get(AgentTaskStep, step_id)

    async def list_steps(self, task_id: UUID) -> list[AgentTaskStep]:
        result = await self.session.execute(
            select(AgentTaskStep)
            .where(AgentTaskStep.task_id == task_id)
            .order_by(AgentTaskStep.started_at.asc(), AgentTaskStep.step_name.asc())
        )
        return list(result.scalars())
