from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sellpilot.core.enums import ToolCallStatus, ToolRiskLevel
from sellpilot.db.base import JSON_TYPE, Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from sellpilot.db.models.agent_task import AgentTask


class ToolCall(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tool_calls"
    __table_args__ = (
        Index("ix_tool_calls_task_id_created_at", "task_id", "created_at"),
        Index("ix_tool_calls_status_created_at", "status", "created_at"),
        Index("ix_tool_calls_request_id", "request_id"),
        Index("ix_tool_calls_confirmation_id", "confirmation_id"),
        Index("ix_tool_calls_idempotency_key", "idempotency_key"),
    )

    task_id: Mapped[UUID | None] = mapped_column(ForeignKey("agent_tasks.id", ondelete="CASCADE"))
    task_step_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_task_steps.id", ondelete="SET NULL")
    )
    confirmation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("confirmation_tasks.id", ondelete="SET NULL")
    )
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tool_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default=ToolRiskLevel.READ, nullable=False)
    caller_type: Mapped[str] = mapped_column(String(32), nullable=False)
    caller_name: Mapped[str | None] = mapped_column(String(100))
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    input_digest: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default=ToolCallStatus.PENDING, nullable=False)
    input_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    output_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    attempt_history: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    task: Mapped["AgentTask | None"] = relationship(back_populates="tool_calls")
