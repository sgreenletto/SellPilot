from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.knowledge_base import KnowledgeChunk, KnowledgeDocument


class KnowledgeDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def get(self, document_id: UUID) -> KnowledgeDocument | None:
        return await self.session.get(KnowledgeDocument, document_id)

    async def list(
        self,
        page: int,
        page_size: int,
        *,
        category: str | None = None,
        status: str | None = None,
    ) -> tuple[list[KnowledgeDocument], int]:
        statement = select(KnowledgeDocument)
        count_statement = select(func.count()).select_from(KnowledgeDocument)
        predicates = []
        if category is not None:
            predicates.append(KnowledgeDocument.category == category)
        if status is not None:
            predicates.append(KnowledgeDocument.status == status)
        if predicates:
            statement = statement.where(*predicates)
            count_statement = count_statement.where(*predicates)
        total = await self.session.scalar(count_statement)
        result = await self.session.execute(
            statement.order_by(KnowledgeDocument.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)

    async def delete(self, document_id: UUID) -> None:
        doc = await self.get(document_id)
        if doc is not None:
            await self.session.delete(doc)
            await self.session.flush()


class KnowledgeChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def add_all(self, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
        self.session.add_all(chunks)
        await self.session.flush()
        return chunks

    async def get(self, chunk_id: UUID) -> KnowledgeChunk | None:
        return await self.session.get(KnowledgeChunk, chunk_id)

    async def list_by_document(
        self,
        document_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[KnowledgeChunk], int]:
        predicate = KnowledgeChunk.document_id == document_id
        total = await self.session.scalar(
            select(func.count()).select_from(KnowledgeChunk).where(predicate)
        )
        result = await self.session.execute(
            select(KnowledgeChunk)
            .where(predicate)
            .order_by(KnowledgeChunk.chunk_index)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), int(total or 0)

    async def delete_by_document(self, document_id: UUID) -> int:
        """删除文档下所有 chunk，返回删除数量。"""
        result = await self.session.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
        )
        chunks = list(result.scalars())
        for chunk in chunks:
            await self.session.delete(chunk)
        await self.session.flush()
        return len(chunks)
