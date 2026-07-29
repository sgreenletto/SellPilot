from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Uuid
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
        Index("ix_agent_tasks_workflow_status", "workflow_name", "status"),
        Index("ix_agent_tasks_parent_task_id", "parent_task_id"),
        Index("ix_agent_tasks_lease_expires_at", "lease_expires_at"),
    )

    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_name: Mapped[str] = mapped_column(String(100), default="diagnostic", nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    workflow_input: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    parent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.PENDING, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(100))
    current_node: Mapped[str | None] = mapped_column(String(100))
    serialized_state: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE, default=dict, nullable=False
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    task_attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    request_id: Mapped[str] = mapped_column(
        String(64),
        default="00000000-0000-0000-0000-000000000000",
        nullable=False,
    )
    execution_token: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    runner_id: Mapped[str | None] = mapped_column(String(100))
    execution_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    creator: Mapped["User"] = relationship(back_populates="created_tasks")
    parent_task: Mapped["AgentTask | None"] = relationship(
        remote_side="AgentTask.id",
        back_populates="reruns",
    )
    reruns: Mapped[list["AgentTask"]] = relationship(back_populates="parent_task")
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
