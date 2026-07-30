from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.knowledge_base import KnowledgeChunk, KnowledgeDocument
from sellpilot.db.models.user import User
from sellpilot.services import knowledge_ingestion
from sellpilot.services.knowledge_ingestion import KnowledgeIngestionService


class FakeLLMService:
    def __init__(self, settings: object) -> None:
        self.settings = settings

    async def chat(self, messages: list[dict[str, str]], **kwargs: object) -> str:
        return "测试翻译"


class FakeEmbeddingService:
    _model_name = "fake-embedding"

    @property
    def dim(self) -> int:
        return 2

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[0.5, 0.5] for _ in texts]


class FakeVectorStore:
    _collection_name = "test"

    def __init__(self) -> None:
        self.document_ids: set[UUID] = set()
        self.deleted_ids: list[UUID] = []

    @property
    def count(self) -> int:
        return len(self.document_ids)

    def upsert_chunks(
        self,
        document_id: UUID,
        chunk_indices: list[int],
        texts: list[str],
        embeddings: list[list[float]],
        metadata_list: list[dict] | None = None,
    ) -> None:
        self.document_ids.add(document_id)

    def delete_by_document(self, document_id: UUID) -> int:
        self.deleted_ids.append(document_id)
        existed = document_id in self.document_ids
        self.document_ids.discard(document_id)
        return int(existed)


def _write_import_package(path: Path) -> None:
    (path / "products.csv").write_text(
        "product_id,title,category_name,description,site,price,currency,sales_count\n"
        "PROD-TEST,Test Product,Demo,Description,SG,10,SGD,5\n",
        encoding="utf-8",
    )
    (path / "reviews.csv").write_text(
        "review_id,content,content_zh,language,issue_type,sentiment_hint,rating\n"
        "REV-TEST,Good product,好商品,en,,positive,5\n",
        encoding="utf-8",
    )
    (path / "customer_sessions.csv").write_text(
        "session_id,language,intent,risk_level\nSESSION-TEST,en,product_question,low\n",
        encoding="utf-8",
    )
    (path / "customer_messages.csv").write_text(
        "session_id,sender_type,content\n"
        "SESSION-TEST,buyer,Is it available?\n"
        "SESSION-TEST,assistant,Yes it is available.\n",
        encoding="utf-8",
    )


async def _add_document(
    session: AsyncSession,
    *,
    owner: User,
    title: str,
    source: str,
    is_mock_data: bool,
) -> KnowledgeDocument:
    document = KnowledgeDocument(
        title=title,
        file_type="text",
        category="policy",
        status="indexed",
        source=source,
        chunk_count=1,
        is_mock_data=is_mock_data,
        created_by=owner.id,
    )
    session.add(document)
    await session.flush()
    session.add(
        KnowledgeChunk(
            document_id=document.id,
            chunk_index=0,
            content=title,
            chunk_size=len(title),
            is_mock_data=is_mock_data,
        )
    )
    await session.flush()
    return document


@pytest.mark.asyncio
async def test_full_rebuild_preserves_non_rebuild_documents(
    session: AsyncSession,
    admin_user: User,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_import_package(tmp_path)
    user_document = await _add_document(
        session,
        owner=admin_user,
        title="User policy",
        source="uploads/user-policy.pdf",
        is_mock_data=False,
    )
    mock_policy = await _add_document(
        session,
        owner=admin_user,
        title="Mock policy",
        source="knowledge_mock/return-policy.md",
        is_mock_data=True,
    )
    replaced = await _add_document(
        session,
        owner=admin_user,
        title="Old product",
        source="products.csv#OLD",
        is_mock_data=True,
    )

    vector_store = FakeVectorStore()
    vector_store.document_ids.add(replaced.id)
    monkeypatch.setattr(knowledge_ingestion, "LLMService", FakeLLMService)
    monkeypatch.setattr(knowledge_ingestion, "EmbeddingService", FakeEmbeddingService)
    monkeypatch.setattr(
        knowledge_ingestion,
        "ChromaVectorStore",
        lambda: vector_store,
    )

    service = KnowledgeIngestionService(session)
    result = await service.import_package(tmp_path)
    await session.commit()
    removed_vectors = service.finalize_rebuild_vectors()

    documents = list((await session.execute(select(KnowledgeDocument))).scalars())
    document_ids = {document.id for document in documents}
    sources = {document.source for document in documents}

    assert user_document.id in document_ids
    assert mock_policy.id in document_ids
    assert replaced.id not in document_ids
    assert "products.csv#PROD-TEST" in sources
    assert "reviews.csv#REV-TEST" in sources
    assert "customer_messages.csv#SESSION-TEST" in sources
    assert result["replaced_documents"] == 1
    assert result["preserved_non_rebuild_documents"] is True
    assert removed_vectors == 1
    assert vector_store.deleted_ids == [replaced.id]


def test_rebuild_source_scope_is_explicit() -> None:
    assert KnowledgeIngestionService.is_rebuild_source("products.csv#PROD-001")
    assert KnowledgeIngestionService.is_rebuild_source("reviews.csv#REV-001")
    assert KnowledgeIngestionService.is_rebuild_source("customer_messages.csv#SESSION-001")
    assert not KnowledgeIngestionService.is_rebuild_source("knowledge_mock/return-policy.md")
    assert not KnowledgeIngestionService.is_rebuild_source("uploads/user-policy.pdf")
