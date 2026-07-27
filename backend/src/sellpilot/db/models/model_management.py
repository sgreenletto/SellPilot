from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sellpilot.core.enums import PromptStatus
from sellpilot.db.base import (
    JSON_TYPE,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    utc_now,
)


class PromptTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prompt_templates"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=PromptStatus.ACTIVE, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    versions: Mapped[list["PromptVersion"]] = relationship(back_populates="template")


class PromptVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "version",
            name="uq_prompt_versions_template_version",
        ),
        UniqueConstraint(
            "template_id",
            "checksum",
            name="uq_prompt_versions_template_checksum",
        ),
        CheckConstraint("version > 0", name="version_positive"),
        Index("ix_prompt_versions_template_created_at", "template_id", "created_at"),
    )

    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("prompt_templates.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    model_config: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    template: Mapped["PromptTemplate"] = relationship(back_populates="versions")


class ModelInvocation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "model_invocations"
    __table_args__ = (
        CheckConstraint("prompt_tokens >= 0", name="prompt_tokens_nonnegative"),
        CheckConstraint("completion_tokens >= 0", name="completion_tokens_nonnegative"),
        CheckConstraint("total_tokens >= 0", name="total_tokens_nonnegative"),
        CheckConstraint("duration_ms >= 0", name="duration_ms_nonnegative"),
        CheckConstraint("timeout_ms > 0", name="timeout_ms_positive"),
        CheckConstraint("retry_count >= 0", name="retry_count_nonnegative"),
        CheckConstraint("estimated_cost >= 0", name="estimated_cost_nonnegative"),
        Index("ix_model_invocations_status_created_at", "status", "created_at"),
        Index("ix_model_invocations_model_created_at", "model_name", "created_at"),
        Index("ix_model_invocations_agent_task_id", "agent_task_id"),
    )

    agent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="RESTRICT")
    )
    prompt_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="RESTRICT")
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    input_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    output_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    model_parameters: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    cost_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
