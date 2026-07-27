from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sellpilot.core.enums import RiskLevel, ToolCallStatus
from sellpilot.db.base import JSON_TYPE, Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from sellpilot.db.models.agent_task import AgentTask


class ToolCall(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tool_calls"
    __table_args__ = (Index("ix_tool_calls_task_id_created_at", "task_id", "created_at"),)

    task_id: Mapped[UUID | None] = mapped_column(ForeignKey("agent_tasks.id", ondelete="CASCADE"))
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(32), default=RiskLevel.READ, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=ToolCallStatus.SUCCEEDED, nullable=False
    )
    input_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    output_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    task: Mapped["AgentTask | None"] = relationship(back_populates="tool_calls")
