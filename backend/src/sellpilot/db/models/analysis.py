from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
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

from sellpilot.core.enums import (
    AnalysisStatus,
    ImprovementReportStatus,
    ImprovementSuggestionStatus,
)
from sellpilot.db.base import (
    JSON_TYPE,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    utc_now,
)


class ProductSelectionTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_selection_tasks"
    __table_args__ = (
        Index("ix_product_selection_tasks_status_created_at", "status", "created_at"),
        Index(
            "ix_product_selection_tasks_created_by_created_at",
            "created_by",
            "created_at",
        ),
    )

    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    agent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(32), default=AnalysisStatus.PENDING, nullable=False)
    criteria: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_snapshot_version: Mapped[str | None] = mapped_column(String(100))
    is_mock_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    results: Mapped[list["ProductSelectionResult"]] = relationship(back_populates="task")


class ProductSelectionResult(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_selection_results"
    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "source_product_id",
            name="uq_product_selection_results_task_product",
        ),
        UniqueConstraint(
            "task_id",
            "rank",
            name="uq_product_selection_results_task_rank",
        ),
        CheckConstraint("rank > 0", name="rank_positive"),
        CheckConstraint(
            "total_score >= 0 AND total_score <= 100",
            name="total_score_range",
        ),
        CheckConstraint(
            "data_completeness >= 0 AND data_completeness <= 1",
            name="data_completeness_range",
        ),
        Index("ix_product_selection_results_task_rank", "task_id", "rank"),
        Index(
            "ix_product_selection_results_product_created_at",
            "source_product_id",
            "created_at",
        ),
    )

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_selection_tasks.id", ondelete="RESTRICT"), nullable=False
    )
    source_product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    site: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    is_mock_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    metric_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_warnings: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    data_completeness: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    data_sources: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    source_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    task: Mapped["ProductSelectionTask"] = relationship(back_populates="results")


class ReviewAnalysisResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "review_analysis_results"
    __table_args__ = (
        Index("ix_review_analysis_results_status_created_at", "status", "created_at"),
        Index(
            "ix_review_analysis_results_product_created_at",
            "source_product_id",
            "created_at",
        ),
    )

    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    agent_task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_tasks.id", ondelete="RESTRICT")
    )
    source_product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    site: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_languages: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    input_conditions: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=AnalysisStatus.PENDING, nullable=False)
    analyzer_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_snapshot_version: Mapped[str | None] = mapped_column(String(100))
    prompt_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="RESTRICT")
    )
    model_invocation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="RESTRICT")
    )
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    is_mock_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    evidence_items: Mapped[list["ReviewAnalysisEvidence"]] = relationship(back_populates="result")
    improvement_reports: Mapped[list["ProductImprovementReport"]] = relationship(
        back_populates="review_analysis_result"
    )


class ReviewAnalysisEvidence(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "review_analysis_evidence"
    __table_args__ = (
        UniqueConstraint(
            "result_id",
            "source_review_id",
            "evidence_type",
            "label",
            name="uq_review_analysis_evidence_identity",
        ),
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index(
            "ix_review_analysis_evidence_result_type",
            "result_id",
            "evidence_type",
        ),
        Index(
            "ix_review_analysis_evidence_source_review",
            "source_review_id",
        ),
    )

    result_id: Mapped[UUID] = mapped_column(
        ForeignKey("review_analysis_results.id", ondelete="RESTRICT"), nullable=False
    )
    source_review_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    is_mock_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    sentiment: Mapped[str | None] = mapped_column(String(32))
    issue_type: Mapped[str | None] = mapped_column(String(100))
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    translated_excerpt: Mapped[str | None] = mapped_column(Text)
    source_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    evidence_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    result: Mapped["ReviewAnalysisResult"] = relationship(back_populates="evidence_items")


class ProductImprovementReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_improvement_reports"
    __table_args__ = (
        UniqueConstraint(
            "review_analysis_result_id",
            "version",
            name="uq_product_improvement_reports_result_version",
        ),
        CheckConstraint("version > 0", name="version_positive"),
        Index(
            "ix_product_improvement_reports_product_status",
            "source_product_id",
            "status",
        ),
    )

    review_analysis_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("review_analysis_results.id", ondelete="RESTRICT"), nullable=False
    )
    source_product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=ImprovementReportStatus.DRAFT, nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    is_mock_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    data_sources: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    input_conditions: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    prompt_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="RESTRICT")
    )
    model_invocation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="RESTRICT")
    )
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    review_analysis_result: Mapped["ReviewAnalysisResult"] = relationship(
        back_populates="improvement_reports"
    )
    suggestions: Mapped[list["ProductImprovementSuggestion"]] = relationship(
        back_populates="report"
    )


class ProductImprovementSuggestion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_improvement_suggestions"
    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "suggestion_key",
            name="uq_product_improvement_suggestions_report_key",
        ),
        CheckConstraint("priority >= 1 AND priority <= 5", name="priority_range"),
        CheckConstraint(
            "severity >= 0 AND severity <= 1",
            name="severity_range",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        CheckConstraint(
            "frequency_rate >= 0 AND frequency_rate <= 1",
            name="frequency_rate_range",
        ),
        CheckConstraint("evidence_count >= 0", name="evidence_count_nonnegative"),
        Index(
            "ix_product_improvement_suggestions_report_priority",
            "report_id",
            "priority",
        ),
    )

    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_improvement_reports.id", ondelete="RESTRICT"),
        nullable=False,
    )
    suggestion_key: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    evidence_review_ids: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    expected_impact: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    status: Mapped[str] = mapped_column(
        String(32),
        default=ImprovementSuggestionStatus.PROPOSED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    report: Mapped["ProductImprovementReport"] = relationship(back_populates="suggestions")
