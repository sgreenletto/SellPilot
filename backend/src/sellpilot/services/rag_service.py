"""Grounded knowledge retrieval and answer generation over the existing knowledge index."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.db.models.knowledge_base import KnowledgeChunk, KnowledgeDocument
from sellpilot.services.embedding import EmbeddingService
from sellpilot.services.llm_service import LLMService
from sellpilot.services.vector_store import ChromaVectorStore

NO_RELIABLE_ANSWER = "当前知识库中没有找到可靠依据。"
KNOWLEDGE_NOT_INITIALIZED = "当前知识库尚未完成初始化，请先导入知识数据。"
SYSTEM_PROMPT = """You are SellPilot AI, a cross-border e-commerce operations assistant.
Answer only from the supplied knowledge fragments. Do not invent facts.
If the fragments are insufficient, state that there is no reliable basis.
Cite source labels and answer in the same language as the question."""


class RAGService:
    """Reuse the single Chroma vector index and PostgreSQL knowledge metadata."""

    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self._settings = settings
        self._session = session

    @staticmethod
    def _terms(query: str) -> tuple[str, ...]:
        normalized = query.casefold().strip()
        words = re.findall(r"[a-z0-9][a-z0-9_-]*|[\u3400-\u9fff]{2,}", normalized)
        terms: set[str] = set(words)
        for word in words:
            if re.fullmatch(r"[\u3400-\u9fff]{3,}", word):
                terms.update(word[index : index + 2] for index in range(len(word) - 1))
        return tuple(sorted(terms, key=lambda item: (-len(item), item)))

    @classmethod
    def _lexical_score(cls, query: str, content: str, title: str) -> float:
        terms = cls._terms(query)
        if not terms:
            return 0.0
        haystack = f"{title}\n{content}".casefold()
        matched_weight = sum(len(term) for term in terms if term in haystack)
        total_weight = sum(len(term) for term in terms)
        phrase_bonus = 0.25 if query.casefold().strip() in haystack else 0.0
        return round(min(1.0, matched_weight / max(total_weight, 1) + phrase_bonus), 4)

    async def _retrieve_unembedded(
        self,
        query: str,
        *,
        top_k: int,
        category: str | None,
    ) -> list[dict[str, Any]]:
        """Retrieve indexed chunks that have not yet entered the vector index."""

        statement = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(
                KnowledgeDocument.status == "indexed",
                KnowledgeChunk.embedding_status != "embedded",
            )
            .order_by(KnowledgeDocument.updated_at.desc(), KnowledgeChunk.chunk_index.asc())
            .limit(2000)
        )
        if category:
            statement = statement.where(KnowledgeDocument.category == category)
        rows = (await self._session.execute(statement)).all()
        ranked: list[dict[str, Any]] = []
        for chunk, document in rows:
            score = self._lexical_score(query, chunk.content, document.title)
            if score <= 0:
                continue
            metadata = document.metadata_json or {}
            ranked.append(
                {
                    "fragment": chunk.content[:1200],
                    "score": score,
                    "source_doc": document.source or document.title,
                    "document_id": str(document.id),
                    "chunk_index": chunk.chunk_index,
                    "category": document.category,
                    "language": str(metadata.get("language") or "zh-CN"),
                    "updated_at": document.updated_at,
                    "is_mock_data": document.is_mock_data,
                }
            )
        ranked.sort(key=lambda item: (-float(item["score"]), str(item["document_id"])))
        return ranked[:top_k]

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        if not await self.has_indexed_knowledge():
            return []
        if not await self.has_embedded_knowledge():
            return await self._retrieve_unembedded(
                query,
                top_k=min(max(top_k, 1), 20),
                category=category,
            )

        embedding_service = EmbeddingService()
        vector_store = ChromaVectorStore()
        query_vector = embedding_service.encode_single(query)
        where = {"category": category} if category else None
        vector_results = vector_store.search(
            query_vector,
            top_k=min(max(top_k, 1), 20),
            where=where,
        )

        document_ids: list[UUID] = []
        for item in vector_results:
            raw_id = item.get("metadata", {}).get("document_id")
            try:
                document_ids.append(UUID(str(raw_id)))
            except (TypeError, ValueError):
                continue
        documents = (
            (
                await self._session.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.id.in_(document_ids))
                )
            )
            .scalars()
            .all()
            if document_ids
            else []
        )
        document_map = {str(document.id): document for document in documents}

        sources: list[dict[str, Any]] = []
        for item in vector_results:
            metadata = item.get("metadata", {})
            document_id = str(metadata.get("document_id") or "")
            document = document_map.get(document_id)
            if document is None or document.status != "indexed":
                continue
            document_metadata = document.metadata_json or {}
            sources.append(
                {
                    "fragment": str(item.get("document") or "")[:1200],
                    "score": float(item.get("score") or 0),
                    "source_doc": str(metadata.get("source") or document.source or document.title),
                    "document_id": document_id,
                    "chunk_index": int(metadata.get("chunk_index") or 0),
                    "category": str(metadata.get("category") or document.category),
                    "language": str(document_metadata.get("language") or "zh-CN"),
                    "updated_at": document.updated_at,
                    "is_mock_data": document.is_mock_data,
                }
            )
        if sources:
            return sources
        return await self._retrieve_unembedded(
            query,
            top_k=min(max(top_k, 1), 20),
            category=category,
        )

    async def has_indexed_knowledge(self) -> bool:
        """Return whether at least one indexed document has a persisted chunk."""

        statement = select(
            exists().where(
                KnowledgeDocument.status == "indexed",
                KnowledgeChunk.document_id == KnowledgeDocument.id,
            )
        )
        return bool(await self._session.scalar(statement))

    async def has_embedded_knowledge(self) -> bool:
        """Return whether PostgreSQL references at least one vectorized chunk."""

        statement = select(
            exists().where(
                KnowledgeDocument.status == "indexed",
                KnowledgeChunk.document_id == KnowledgeDocument.id,
                KnowledgeChunk.embedding_status == "embedded",
            )
        )
        return bool(await self._session.scalar(statement))

    async def ask(
        self,
        question: str,
        *,
        top_k: int = 5,
        category: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        sources = await self.retrieve(question, top_k=top_k, category=category)
        if not sources:
            initialized = await self.has_indexed_knowledge()
            return {
                "answer": NO_RELIABLE_ANSWER if initialized else KNOWLEDGE_NOT_INITIALIZED,
                "sources": [],
                "answer_mode": (
                    "no_reliable_source" if initialized else "knowledge_not_initialized"
                ),
                "knowledge_initialized": initialized,
            }
        if float(sources[0]["score"]) < 0.2:
            return {
                "answer": NO_RELIABLE_ANSWER,
                "sources": [],
                "answer_mode": "no_reliable_source",
                "knowledge_initialized": True,
            }

        api_key = self._settings.llm_api_key.get_secret_value()
        if not api_key:
            source = sources[0]
            return {
                "answer": f"根据知识库“{source['source_doc']}”：{source['fragment']}",
                "sources": sources,
                "answer_mode": "grounded_extract",
                "knowledge_initialized": True,
            }

        context = "\n\n".join(
            f"[{index + 1}] {item['source_doc']}\n{item['fragment']}"
            for index, item in enumerate(sources)
        )
        answer = await LLMService(self._settings).chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Knowledge fragments:\n{context}\n\nQuestion: {question}",
                },
            ],
            temperature=temperature,
        )
        return {
            "answer": answer,
            "sources": sources,
            "answer_mode": "grounded_llm",
            "knowledge_initialized": True,
        }


def serialize_source_timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
