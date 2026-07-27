from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sellpilot.core.enums import ConfirmationStatus, ToolRiskLevel
from sellpilot.db.base import JSON_TYPE, Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from sellpilot.db.models.agent_task import AgentTask
    from sellpilot.db.models.operation_log import OperationLog
    from sellpilot.db.models.user import User


class ConfirmationTask(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "confirmation_tasks"
    __table_args__ = (
        Index("ix_confirmation_tasks_status_created_at", "status", "created_at"),
        Index("ix_confirmation_tasks_agent_task_id", "agent_task_id"),
    )

    agent_task_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="RESTRICT"), nullable=False
    )
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(255))
    risk_level: Mapped[str] = mapped_column(String(32), default=ToolRiskLevel.WRITE, nullable=False)
    before_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    after_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    status: Mapped[str] = mapped_column(
        String(32), default=ConfirmationStatus.PENDING, nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    confirmed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    error_message: Mapped[str | None] = mapped_column(Text)

    agent_task: Mapped["AgentTask"] = relationship(back_populates="confirmation_tasks")
    creator: Mapped["User"] = relationship(
        back_populates="created_confirmations", foreign_keys=[created_by]
    )
    confirmer: Mapped["User | None"] = relationship(
        back_populates="confirmed_confirmations", foreign_keys=[confirmed_by]
    )
    operation_logs: Mapped[list["OperationLog"]] = relationship(
        back_populates="confirmation_task",
        foreign_keys="OperationLog.confirmation_task_id",
    )
