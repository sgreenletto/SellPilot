from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sellpilot.core.enums import GeneratedReportStatus, ProductContentStatus
from sellpilot.db.base import (
    JSON_TYPE,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    utc_now,
)


class ProductContent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_contents"
    __table_args__ = (
        UniqueConstraint(
            "source_product_id",
            "site",
            "target_language",
            name="uq_product_contents_product_site_language",
        ),
        Index(
            "ix_product_contents_product_language_status",
            "source_product_id",
            "target_language",
            "status",
        ),
        Index("ix_product_contents_created_by_created_at", "created_by", "created_at"),
    )

    source_product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    site: Mapped[str] = mapped_column(String(64), nullable=False)
    target_language: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=ProductContentStatus.DRAFT, nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_snapshot_version: Mapped[str | None] = mapped_column(String(100))
    source_facts: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    is_mock_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    agent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="RESTRICT")
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    versions: Mapped[list["ProductContentVersion"]] = relationship(back_populates="content")


class ProductContentVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_content_versions"
    __table_args__ = (
        UniqueConstraint(
            "content_id",
            "version",
            name="uq_product_content_versions_content_version",
        ),
        CheckConstraint("version > 0", name="version_positive"),
        Index(
            "ix_product_content_versions_content_created_at",
            "content_id",
            "created_at",
        ),
    )

    content_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_contents.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    bullet_points: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    marketing_copy: Mapped[str] = mapped_column(Text, nullable=False)
    source_facts_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    faq: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    sku_content: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    keywords: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    fact_check_result: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    compliance_result: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="RESTRICT")
    )
    model_invocation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="RESTRICT")
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    content: Mapped["ProductContent"] = relationship(back_populates="versions")


class GeneratedReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "generated_reports"
    __table_args__ = (
        UniqueConstraint(
            "report_type",
            "source_entity_type",
            "source_entity_id",
            "result_version",
            name="uq_generated_reports_source_version",
        ),
        Index(
            "ix_generated_reports_source",
            "source_entity_type",
            "source_entity_id",
        ),
        Index("ix_generated_reports_status_created_at", "status", "created_at"),
    )

    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    is_mock_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=GeneratedReportStatus.READY, nullable=False
    )
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    data_sources: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    input_conditions: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    model_invocation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="RESTRICT")
    )
    agent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="RESTRICT")
    )
    result_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
