from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.model_management import (
    ModelInvocation,
    PromptTemplate,
    PromptVersion,
)


class PromptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_template(self, template: PromptTemplate) -> PromptTemplate:
        self.session.add(template)
        await self.session.flush()
        return template

    async def get_template(self, template_id: UUID) -> PromptTemplate | None:
        return await self.session.get(PromptTemplate, template_id)

    async def get_template_by_key(self, key: str) -> PromptTemplate | None:
        result = await self.session.execute(select(PromptTemplate).where(PromptTemplate.key == key))
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        page: int,
        page_size: int,
        *,
        status: str | None = None,
    ) -> tuple[list[PromptTemplate], int]:
        statement = select(PromptTemplate)
        count_statement = select(func.count()).select_from(PromptTemplate)
        if status is not None:
            statement = statement.where(PromptTemplate.status == status)
            count_statement = count_statement.where(PromptTemplate.status == status)
        total = await self.session.scalar(count_statement)
        result = await self.session.execute(
            statement.order_by(PromptTemplate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)

    async def add_version(self, version: PromptVersion) -> PromptVersion:
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_version(self, version_id: UUID) -> PromptVersion | None:
        return await self.session.get(PromptVersion, version_id)

    async def get_latest_version(self, template_id: UUID) -> PromptVersion | None:
        result = await self.session.execute(
            select(PromptVersion)
            .where(PromptVersion.template_id == template_id)
            .order_by(PromptVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        template_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[PromptVersion], int]:
        predicate = PromptVersion.template_id == template_id
        total = await self.session.scalar(
            select(func.count()).select_from(PromptVersion).where(predicate)
        )
        result = await self.session.execute(
            select(PromptVersion)
            .where(predicate)
            .order_by(PromptVersion.version.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)


class ModelInvocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, invocation: ModelInvocation) -> ModelInvocation:
        self.session.add(invocation)
        await self.session.flush()
        return invocation

    async def get(self, invocation_id: UUID) -> ModelInvocation | None:
        return await self.session.get(ModelInvocation, invocation_id)

    async def list(
        self,
        page: int,
        page_size: int,
        *,
        status: str | None = None,
        model_name: str | None = None,
    ) -> tuple[list[ModelInvocation], int]:
        statement = select(ModelInvocation)
        count_statement = select(func.count()).select_from(ModelInvocation)
        predicates = []
        if status is not None:
            predicates.append(ModelInvocation.status == status)
        if model_name is not None:
            predicates.append(ModelInvocation.model_name == model_name)
        if predicates:
            statement = statement.where(*predicates)
            count_statement = count_statement.where(*predicates)
        total = await self.session.scalar(count_statement)
        result = await self.session.execute(
            statement.order_by(ModelInvocation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)
