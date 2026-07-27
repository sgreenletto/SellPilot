from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sellpilot.core.enums import OperationStatus
from sellpilot.db.base import JSON_TYPE, Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from sellpilot.db.models.agent_task import AgentTask
    from sellpilot.db.models.confirmation_task import ConfirmationTask
    from sellpilot.db.models.user import User


class OperationLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "operation_logs"
    __table_args__ = (
        Index("ix_operation_logs_target", "target_type", "target_id"),
        Index("ix_operation_logs_request_id", "request_id"),
        Index("ix_operation_logs_created_at", "created_at"),
    )

    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(255))
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="SET NULL")
    )
    confirmation_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("confirmation_tasks.id", ondelete="SET NULL")
    )
    before_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    after_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    status: Mapped[str] = mapped_column(
        String(32), default=OperationStatus.SUCCEEDED, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    actor: Mapped["User | None"] = relationship(back_populates="operation_logs")
    agent_task: Mapped["AgentTask | None"] = relationship(back_populates="operation_logs")
    confirmation_task: Mapped["ConfirmationTask | None"] = relationship(
        back_populates="operation_logs"
    )
