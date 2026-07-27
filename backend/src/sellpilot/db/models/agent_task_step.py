from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sellpilot.core.enums import TaskStepStatus
from sellpilot.db.base import JSON_TYPE, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from sellpilot.db.models.agent_task import AgentTask


class AgentTaskStep(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_task_steps"
    __table_args__ = (Index("ix_agent_task_steps_task_id_status", "task_id", "status"),)

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=TaskStepStatus.PENDING, nullable=False)
    input_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    output_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    task: Mapped["AgentTask"] = relationship(back_populates="steps")
