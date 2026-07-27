from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sellpilot.core.enums import TaskStatus
from sellpilot.db.base import JSON_TYPE, Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from sellpilot.db.models.agent_task_step import AgentTaskStep
    from sellpilot.db.models.confirmation_task import ConfirmationTask
    from sellpilot.db.models.operation_log import OperationLog
    from sellpilot.db.models.tool_call import ToolCall
    from sellpilot.db.models.user import User


class AgentTask(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_tasks"
    __table_args__ = (
        Index("ix_agent_tasks_status_created_at", "status", "created_at"),
        Index("ix_agent_tasks_created_by_created_at", "created_by", "created_at"),
    )

    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.PENDING, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    creator: Mapped["User"] = relationship(back_populates="created_tasks")
    steps: Mapped[list["AgentTaskStep"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )
    tool_calls: Mapped[list["ToolCall"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )
    confirmation_tasks: Mapped[list["ConfirmationTask"]] = relationship(back_populates="agent_task")
    operation_logs: Mapped[list["OperationLog"]] = relationship(
        back_populates="agent_task", foreign_keys="OperationLog.agent_task_id"
    )
