from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.analysis import (
    ProductImprovementReport,
    ProductImprovementSuggestion,
    ProductSelectionResult,
    ProductSelectionTask,
    ReviewAnalysisEvidence,
    ReviewAnalysisResult,
)


class SelectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_task(self, task: ProductSelectionTask) -> ProductSelectionTask:
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_task(self, task_id: UUID) -> ProductSelectionTask | None:
        return await self.session.get(ProductSelectionTask, task_id)

    async def list_tasks(
        self,
        page: int,
        page_size: int,
        *,
        status: str | None = None,
    ) -> tuple[list[ProductSelectionTask], int]:
        statement = select(ProductSelectionTask)
        count_statement = select(func.count()).select_from(ProductSelectionTask)
        if status is not None:
            statement = statement.where(ProductSelectionTask.status == status)
            count_statement = count_statement.where(ProductSelectionTask.status == status)
        total = await self.session.scalar(count_statement)
        result = await self.session.execute(
            statement.order_by(ProductSelectionTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)

    async def add_results(
        self,
        results: Iterable[ProductSelectionResult],
    ) -> list[ProductSelectionResult]:
        result_list = list(results)
        self.session.add_all(result_list)
        await self.session.flush()
        return result_list

    async def list_results(
        self,
        task_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[ProductSelectionResult], int]:
        predicate = ProductSelectionResult.task_id == task_id
        total = await self.session.scalar(
            select(func.count()).select_from(ProductSelectionResult).where(predicate)
        )
        result = await self.session.execute(
            select(ProductSelectionResult)
            .where(predicate)
            .order_by(ProductSelectionResult.rank.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)


class ReviewAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_result(self, result: ReviewAnalysisResult) -> ReviewAnalysisResult:
        self.session.add(result)
        await self.session.flush()
        return result

    async def get_result(self, result_id: UUID) -> ReviewAnalysisResult | None:
        return await self.session.get(ReviewAnalysisResult, result_id)

    async def find_by_idempotency_key(
        self,
        *,
        created_by: UUID,
        source_product_id: str,
        idempotency_key: str,
    ) -> ReviewAnalysisResult | None:
        return await self.session.scalar(
            select(ReviewAnalysisResult)
            .where(
                ReviewAnalysisResult.created_by == created_by,
                ReviewAnalysisResult.source_product_id == source_product_id,
                ReviewAnalysisResult.input_conditions["idempotency_key"].as_string()
                == idempotency_key,
            )
            .order_by(ReviewAnalysisResult.created_at.desc())
            .limit(1)
        )

    async def list_results(
        self,
        page: int,
        page_size: int,
        *,
        status: str | None = None,
        source_product_id: str | None = None,
    ) -> tuple[list[ReviewAnalysisResult], int]:
        statement = select(ReviewAnalysisResult)
        count_statement = select(func.count()).select_from(ReviewAnalysisResult)
        predicates = []
        if status is not None:
            predicates.append(ReviewAnalysisResult.status == status)
        if source_product_id is not None:
            predicates.append(ReviewAnalysisResult.source_product_id == source_product_id)
        if predicates:
            statement = statement.where(*predicates)
            count_statement = count_statement.where(*predicates)
        total = await self.session.scalar(count_statement)
        result = await self.session.execute(
            statement.order_by(ReviewAnalysisResult.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)

    async def add_evidence(
        self,
        evidence_items: Iterable[ReviewAnalysisEvidence],
    ) -> list[ReviewAnalysisEvidence]:
        evidence_list = list(evidence_items)
        self.session.add_all(evidence_list)
        await self.session.flush()
        return evidence_list

    async def list_evidence(
        self,
        result_id: UUID,
        page: int,
        page_size: int,
        *,
        evidence_type: str | None = None,
        label: str | None = None,
    ) -> tuple[list[ReviewAnalysisEvidence], int]:
        predicates = [ReviewAnalysisEvidence.result_id == result_id]
        if evidence_type is not None:
            predicates.append(ReviewAnalysisEvidence.evidence_type == evidence_type)
        if label is not None:
            predicates.append(ReviewAnalysisEvidence.label == label)
        total = await self.session.scalar(
            select(func.count()).select_from(ReviewAnalysisEvidence).where(*predicates)
        )
        result = await self.session.execute(
            select(ReviewAnalysisEvidence)
            .where(*predicates)
            .order_by(
                ReviewAnalysisEvidence.confidence.desc(),
                ReviewAnalysisEvidence.created_at.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)


class ImprovementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_report(
        self,
        report: ProductImprovementReport,
    ) -> ProductImprovementReport:
        self.session.add(report)
        await self.session.flush()
        return report

    async def get_report(self, report_id: UUID) -> ProductImprovementReport | None:
        return await self.session.get(ProductImprovementReport, report_id)

    async def get_suggestion(self, suggestion_id: UUID) -> ProductImprovementSuggestion | None:
        return await self.session.get(ProductImprovementSuggestion, suggestion_id)

    async def list_reports(
        self,
        page: int,
        page_size: int,
        *,
        status: str | None = None,
        source_product_id: str | None = None,
    ) -> tuple[list[ProductImprovementReport], int]:
        statement = select(ProductImprovementReport)
        count_statement = select(func.count()).select_from(ProductImprovementReport)
        predicates = []
        if status is not None:
            predicates.append(ProductImprovementReport.status == status)
        if source_product_id is not None:
            predicates.append(ProductImprovementReport.source_product_id == source_product_id)
        if predicates:
            statement = statement.where(*predicates)
            count_statement = count_statement.where(*predicates)
        total = await self.session.scalar(count_statement)
        result = await self.session.execute(
            statement.order_by(ProductImprovementReport.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)

    async def add_suggestions(
        self,
        suggestions: Iterable[ProductImprovementSuggestion],
    ) -> list[ProductImprovementSuggestion]:
        suggestion_list = list(suggestions)
        self.session.add_all(suggestion_list)
        await self.session.flush()
        return suggestion_list

    async def list_suggestions(
        self,
        report_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[ProductImprovementSuggestion], int]:
        predicate = ProductImprovementSuggestion.report_id == report_id
        total = await self.session.scalar(
            select(func.count()).select_from(ProductImprovementSuggestion).where(predicate)
        )
        result = await self.session.execute(
            select(ProductImprovementSuggestion)
            .where(predicate)
            .order_by(
                ProductImprovementSuggestion.priority.asc(),
                ProductImprovementSuggestion.created_at.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)
