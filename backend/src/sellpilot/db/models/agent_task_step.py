from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sellpilot.core.enums import TaskStepStatus
from sellpilot.db.base import JSON_TYPE, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from sellpilot.db.models.agent_task import AgentTask


class AgentTaskStep(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_task_steps"
    __table_args__ = (
        Index("ix_agent_task_steps_task_id_status", "task_id", "status"),
        Index("ix_agent_task_steps_tool_call_id", "tool_call_id"),
        Index("ix_agent_task_steps_confirmation_id", "confirmation_id"),
        UniqueConstraint("task_id", "sequence", name="uq_agent_task_steps_task_sequence"),
    )

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=TaskStepStatus.PENDING, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    output_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    tool_call_id: Mapped[UUID | None] = mapped_column()
    confirmation_id: Mapped[UUID | None] = mapped_column()
    step_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON_TYPE)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    task: Mapped["AgentTask"] = relationship(back_populates="steps")

    @property
    def node_name(self) -> str:
        return self.step_name

    @property
    def completed_at(self) -> datetime | None:
        return self.finished_at
