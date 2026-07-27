from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.content import (
    GeneratedReport,
    ProductContent,
    ProductContentVersion,
)


class ProductContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_content(self, content: ProductContent) -> ProductContent:
        self.session.add(content)
        await self.session.flush()
        return content

    async def get_content(self, content_id: UUID) -> ProductContent | None:
        return await self.session.get(ProductContent, content_id)

    async def list_contents(
        self,
        page: int,
        page_size: int,
        *,
        status: str | None = None,
        source_product_id: str | None = None,
    ) -> tuple[list[ProductContent], int]:
        statement = select(ProductContent)
        count_statement = select(func.count()).select_from(ProductContent)
        predicates = []
        if status is not None:
            predicates.append(ProductContent.status == status)
        if source_product_id is not None:
            predicates.append(ProductContent.source_product_id == source_product_id)
        if predicates:
            statement = statement.where(*predicates)
            count_statement = count_statement.where(*predicates)
        total = await self.session.scalar(count_statement)
        result = await self.session.execute(
            statement.order_by(ProductContent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)

    async def add_version(
        self,
        version: ProductContentVersion,
    ) -> ProductContentVersion:
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_version(
        self,
        version_id: UUID,
    ) -> ProductContentVersion | None:
        return await self.session.get(ProductContentVersion, version_id)

    async def list_versions(
        self,
        content_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[ProductContentVersion], int]:
        predicate = ProductContentVersion.content_id == content_id
        total = await self.session.scalar(
            select(func.count()).select_from(ProductContentVersion).where(predicate)
        )
        result = await self.session.execute(
            select(ProductContentVersion)
            .where(predicate)
            .order_by(ProductContentVersion.version.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)


class GeneratedReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, report: GeneratedReport) -> GeneratedReport:
        self.session.add(report)
        await self.session.flush()
        return report

    async def get(self, report_id: UUID) -> GeneratedReport | None:
        return await self.session.get(GeneratedReport, report_id)

    async def list(
        self,
        page: int,
        page_size: int,
        *,
        status: str | None = None,
        source_entity_type: str | None = None,
        source_entity_id: str | None = None,
    ) -> tuple[list[GeneratedReport], int]:
        statement = select(GeneratedReport)
        count_statement = select(func.count()).select_from(GeneratedReport)
        predicates = []
        if status is not None:
            predicates.append(GeneratedReport.status == status)
        if source_entity_type is not None:
            predicates.append(GeneratedReport.source_entity_type == source_entity_type)
        if source_entity_id is not None:
            predicates.append(GeneratedReport.source_entity_id == source_entity_id)
        if predicates:
            statement = statement.where(*predicates)
            count_statement = count_statement.where(*predicates)
        total = await self.session.scalar(count_statement)
        result = await self.session.execute(
            statement.order_by(GeneratedReport.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)
