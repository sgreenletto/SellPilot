from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.db.models.knowledge_base import KnowledgeChunk, KnowledgeDocument
from sellpilot.repositories.knowledge_base import (
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)


class KnowledgeBaseService:
    """知识库文档与切块管理服务。

    当前阶段仅提供基础 CRUD，不包含文件解析、文本切块和向量化。
    后续阶段将在此 Service 中接入解析器和 embedding 流水线。
    """

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.doc_repo = KnowledgeDocumentRepository(session)
        self.chunk_repo = KnowledgeChunkRepository(session)

    # ---- 文档管理 ----

    async def create_document(
        self,
        title: str,
        file_type: str,
        category: str,
        created_by: UUID,
        *,
        file_size_bytes: int = 0,
        source: str | None = None,
        metadata_json: dict | None = None,
    ) -> KnowledgeDocument:
        doc = KnowledgeDocument(
            title=title,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            category=category,
            status="uploaded",
            source=source,
            metadata_json=metadata_json or {},
            created_by=created_by,
        )
        return await self.doc_repo.add(doc)

    async def get_document(self, document_id: UUID) -> KnowledgeDocument | None:
        return await self.doc_repo.get(document_id)

    async def list_documents(
        self,
        page: int,
        page_size: int,
        *,
        category: str | None = None,
        status: str | None = None,
    ) -> tuple[list[KnowledgeDocument], int]:
        return await self.doc_repo.list(page, page_size, category=category, status=status)

    async def update_document_status(
        self,
        document_id: UUID,
        status: str,
        *,
        error_message: str | None = None,
    ) -> KnowledgeDocument | None:
        doc = await self.doc_repo.get(document_id)
        if doc is None:
            return None
        doc.status = status
        if error_message is not None:
            doc.error_message = error_message
        await self.session.flush()
        return doc

    async def delete_document(self, document_id: UUID) -> bool:
        """删除文档及关联的所有 chunk。"""
        doc = await self.doc_repo.get(document_id)
        if doc is None:
            return False
        # 级联删除 chunk（DB 层 CASCADE + 显式删除以保一致性）
        await self.chunk_repo.delete_by_document(document_id)
        await self.doc_repo.delete(document_id)
        return True

    # ---- 切块管理 ----

    async def add_chunks(self, document_id: UUID, chunks: list[dict]) -> list[KnowledgeChunk]:
        """批量添加文本切块。每个 dict 包含 content, chunk_index, metadata_json。"""
        models = [
            KnowledgeChunk(
                document_id=document_id,
                chunk_index=c.get("chunk_index", idx),
                content=c["content"],
                chunk_size=len(c["content"]),
                embedding_status="pending",
                metadata_json=c.get("metadata_json", {}),
            )
            for idx, c in enumerate(chunks)
        ]
        result = await self.chunk_repo.add_all(models)
        # 更新文档的 chunk_count
        doc = await self.doc_repo.get(document_id)
        if doc is not None:
            doc.chunk_count = len(result)
            await self.session.flush()
        return result

    async def list_chunks(
        self, document_id: UUID, page: int, page_size: int
    ) -> tuple[list[KnowledgeChunk], int]:
        return await self.chunk_repo.list_by_document(document_id, page, page_size)

    async def update_chunk_embedding(
        self, chunk_id: UUID, chroma_id: str, status: str = "embedded"
    ) -> KnowledgeChunk | None:
        chunk = await self.chunk_repo.get(chunk_id)
        if chunk is None:
            return None
        chunk.chroma_id = chroma_id
        chunk.embedding_status = status
        await self.session.flush()
        return chunk
