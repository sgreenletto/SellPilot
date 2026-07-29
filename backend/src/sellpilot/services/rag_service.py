"""Grounded knowledge retrieval and answer generation over the existing knowledge tables."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.db.models.knowledge_base import KnowledgeChunk, KnowledgeDocument
from sellpilot.services.llm_service import LLMService

NO_RELIABLE_ANSWER = "当前知识库中没有找到可靠依据。"
SYSTEM_PROMPT = """You are SellPilot AI, a cross-border e-commerce operations assistant.
Answer only from the supplied knowledge fragments. Do not invent facts.
If the fragments are insufficient, state that there is no reliable basis.
Cite source labels and answer in the same language as the question."""


class RAGService:
    """Reuse PostgreSQL knowledge records with bounded, deterministic retrieval."""

    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self.settings = settings
        self.session = session

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
    def _score(cls, query: str, content: str, title: str) -> float:
        terms = cls._terms(query)
        if not terms:
            return 0.0
        haystack = f"{title}\n{content}".casefold()
        matched_weight = sum(len(term) for term in terms if term in haystack)
        total_weight = sum(len(term) for term in terms)
        phrase_bonus = 0.25 if query.casefold().strip() in haystack else 0.0
        return round(min(1.0, matched_weight / max(total_weight, 1) + phrase_bonus), 4)

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        statement = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeDocument.status == "indexed")
            .order_by(KnowledgeDocument.updated_at.desc(), KnowledgeChunk.chunk_index.asc())
            .limit(2000)
        )
        if category:
            statement = statement.where(KnowledgeDocument.category == category)
        rows = (await self.session.execute(statement)).all()
        ranked: list[dict[str, Any]] = []
        for chunk, document in rows:
            score = self._score(query, chunk.content, document.title)
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
        return ranked[: min(max(top_k, 1), 20)]

    async def ask(
        self,
        question: str,
        *,
        top_k: int = 5,
        category: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        sources = await self.retrieve(question, top_k=top_k, category=category)
        if not sources or float(sources[0]["score"]) < 0.2:
            return {
                "answer": NO_RELIABLE_ANSWER,
                "sources": [],
                "answer_mode": "no_reliable_source",
            }

        api_key = self.settings.llm_api_key.get_secret_value()
        if not api_key:
            source = sources[0]
            return {
                "answer": f"根据知识库“{source['source_doc']}”：{source['fragment']}",
                "sources": sources,
                "answer_mode": "grounded_extract",
            }

        context = "\n\n".join(
            f"[{index + 1}] {item['source_doc']}\n{item['fragment']}"
            for index, item in enumerate(sources)
        )
        answer = LLMService(self.settings).chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Knowledge fragments:\n{context}\n\nQuestion: {question}",
                },
            ],
            temperature=temperature,
        )
        return {"answer": answer, "sources": sources, "answer_mode": "grounded_llm"}


def serialize_source_timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
