"""RAG Q&A -- ChromaDB vector retrieval + LLM generation."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.services.embedding import EmbeddingService
from sellpilot.services.llm_service import LLMService
from sellpilot.services.vector_store import ChromaVectorStore

SYSTEM_PROMPT = (
    "You are SellPilot AI, a cross-border e-commerce operations assistant. "
    "Answer user questions based on the provided knowledge base content.\n\n"
    "Rules:\n"
    "1. Only answer based on the provided knowledge fragments. "
    "Do not fabricate information.\n"
    "2. If the knowledge base has no relevant information, say so honestly.\n"
    "3. Cite knowledge sources when answering.\n"
    "4. Answer in the same language as the user's question.\n"
    "5. Keep answers concise and professional."
)


class RAGService:
    """Vector retrieval via ChromaDB + LLM answer generation."""

    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self._settings = settings
        self._session = session

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        es = EmbeddingService()
        vs = ChromaVectorStore()
        query_vec = es.encode_single(query)
        where = {"category": category} if category else None
        results = vs.search(query_vec, top_k=top_k, where=where)
        return [
            {
                "fragment": r["document"],
                "score": r["score"],
                "source_doc": r.get("metadata", {}).get("source", ""),
                "document_id": r.get("metadata", {}).get("document_id", ""),
                "chunk_index": r.get("metadata", {}).get("chunk_index", 0),
                "category": r.get("metadata", {}).get("category", ""),
            }
            for r in results
        ]

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
            return {
                "answer": "当前知识库中没有找到可靠依据。",
                "sources": [],
            }

        api_key = self._settings.llm_api_key.get_secret_value()
        if not api_key:
            return {
                "answer": f"根据知识库「{sources[0]['source_doc']}」：{sources[0]['fragment']}",
                "sources": sources,
            }

        context = "\n\n".join(
            f"[{i + 1}] {s['source_doc']}\n{s['fragment']}"
            for i, s in enumerate(sources)
        )
        llm = LLMService(self._settings)
        answer = await llm.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Knowledge fragments:\n{context}\n\nQuestion: {question}"},
            ],
            temperature=temperature,
        )
        return {"answer": answer, "sources": sources}
