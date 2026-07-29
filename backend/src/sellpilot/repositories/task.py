from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.enums import TaskStatus, TaskStepStatus
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.agent_task_step import AgentTaskStep


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, task: AgentTask) -> AgentTask:
        self.session.add(task)
        await self.session.flush()
        return task

    async def add_step(self, step: AgentTaskStep) -> AgentTaskStep:
        self.session.add(step)
        await self.session.flush()
        return step

    async def get(self, task_id: UUID) -> AgentTask | None:
        return await self.session.get(AgentTask, task_id)

    async def get_owned(self, task_id: UUID, user_id: UUID) -> AgentTask | None:
        result = await self.session.execute(
            select(AgentTask).where(
                AgentTask.id == task_id,
                AgentTask.created_by == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_owned_by_request_id(
        self,
        *,
        user_id: UUID,
        request_id: str,
    ) -> AgentTask | None:
        result = await self.session.execute(
            select(AgentTask)
            .where(
                AgentTask.created_by == user_id,
                AgentTask.request_id == request_id,
            )
            .order_by(AgentTask.created_at.asc(), AgentTask.id.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_recent_assistant_tasks(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[AgentTask]:
        result = await self.session.execute(
            select(AgentTask)
            .where(
                AgentTask.created_by == user_id,
                AgentTask.user_input.like('{"source":"assistant",%'),
            )
            .order_by(AgentTask.created_at.desc(), AgentTask.id.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def get_step(self, step_id: UUID) -> AgentTaskStep | None:
        return await self.session.get(AgentTaskStep, step_id)

    async def list_steps(self, task_id: UUID) -> list[AgentTaskStep]:
        result = await self.session.execute(
            select(AgentTaskStep)
            .where(AgentTaskStep.task_id == task_id)
            .order_by(AgentTaskStep.sequence.asc())
        )
        return list(result.scalars())

    async def latest_step(
        self,
        task_id: UUID,
        *,
        status: TaskStepStatus | None = None,
    ) -> AgentTaskStep | None:
        statement = select(AgentTaskStep).where(AgentTaskStep.task_id == task_id)
        if status is not None:
            statement = statement.where(func.lower(AgentTaskStep.status) == status.value)
        result = await self.session.execute(
            statement.order_by(AgentTaskStep.sequence.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def next_sequence(self, task_id: UUID) -> int:
        current = await self.session.scalar(
            select(func.max(AgentTaskStep.sequence)).where(AgentTaskStep.task_id == task_id)
        )
        return int(current or 0) + 1

    @staticmethod
    def _apply_filters(
        statement: Select[tuple[AgentTask]],
        *,
        user_id: UUID | None,
        status: TaskStatus | None,
        workflow_name: str | None,
        task_type: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> Select[tuple[AgentTask]]:
        if user_id is not None:
            statement = statement.where(AgentTask.created_by == user_id)
        if status is not None:
            statement = statement.where(func.lower(AgentTask.status) == status.value)
        if workflow_name is not None:
            statement = statement.where(AgentTask.workflow_name == workflow_name)
        if task_type is not None:
            statement = statement.where(AgentTask.task_type == task_type)
        if created_from is not None:
            statement = statement.where(AgentTask.created_at >= created_from)
        if created_to is not None:
            statement = statement.where(AgentTask.created_at <= created_to)
        return statement

    async def list(
        self,
        page: int,
        page_size: int,
        *,
        user_id: UUID | None = None,
        status: TaskStatus | None = None,
        workflow_name: str | None = None,
        task_type: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[AgentTask], int]:
        query = self._apply_filters(
            select(AgentTask),
            user_id=user_id,
            status=status,
            workflow_name=workflow_name,
            task_type=task_type,
            created_from=created_from,
            created_to=created_to,
        )
        count_query = self._apply_filters(
            select(AgentTask),
            user_id=user_id,
            status=status,
            workflow_name=workflow_name,
            task_type=task_type,
            created_from=created_from,
            created_to=created_to,
        ).with_only_columns(func.count())
        total = await self.session.scalar(count_query)
        result = await self.session.execute(
            query.order_by(AgentTask.created_at.desc(), AgentTask.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)

    async def add_steps(self, steps: list[AgentTaskStep]) -> list[AgentTaskStep]:
        self.session.add_all(steps)
        await self.session.flush()
        return steps

    async def claim_execution(
        self,
        task_id: UUID,
        *,
        user_id: UUID,
        expected_status: TaskStatus,
        execution_token: UUID,
        runner_id: str,
        now: datetime,
        lease_expires_at: datetime,
        increment_attempt: bool,
    ) -> AgentTask | None:
        values: dict[str, object] = {
            "status": TaskStatus.RUNNING.value,
            "execution_token": execution_token,
            "runner_id": runner_id,
            "execution_started_at": now,
            "heartbeat_at": now,
            "lease_expires_at": lease_expires_at,
            "started_at": func.coalesce(AgentTask.started_at, now),
            "finished_at": None,
        }
        if increment_attempt:
            values["task_attempt"] = AgentTask.task_attempt + 1
        result = await self.session.execute(
            update(AgentTask)
            .where(
                AgentTask.id == task_id,
                AgentTask.created_by == user_id,
                func.lower(AgentTask.status) == expected_status.value,
                AgentTask.execution_token.is_(None),
            )
            .values(**values)
        )
        if result.rowcount != 1:
            return None
        task = await self.get(task_id)
        if task is not None:
            await self.session.refresh(task)
        return task

    async def cancel_owned(
        self,
        task_id: UUID,
        *,
        user_id: UUID,
        now: datetime,
    ) -> AgentTask | None:
        result = await self.session.execute(
            update(AgentTask)
            .where(
                AgentTask.id == task_id,
                AgentTask.created_by == user_id,
                func.lower(AgentTask.status).in_(
                    {
                        TaskStatus.PENDING.value,
                        TaskStatus.RUNNING.value,
                        TaskStatus.WAITING_CONFIRMATION.value,
                    }
                ),
            )
            .values(
                status=TaskStatus.CANCELLED.value,
                finished_at=now,
                execution_token=None,
                runner_id=None,
                heartbeat_at=now,
                lease_expires_at=None,
            )
        )
        if result.rowcount != 1:
            return None
        task = await self.get(task_id)
        if task is not None:
            await self.session.refresh(task)
        return task

    async def list_stale_running(
        self,
        *,
        heartbeat_before: datetime,
        limit: int = 100,
    ) -> list[AgentTask]:
        result = await self.session.execute(
            select(AgentTask)
            .where(
                func.lower(AgentTask.status) == TaskStatus.RUNNING.value,
                AgentTask.heartbeat_at <= heartbeat_before,
            )
            .order_by(AgentTask.heartbeat_at.asc())
            .limit(limit)
        )
        return list(result.scalars())
