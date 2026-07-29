"""RAG Q&A 服务 —— 检索增强生成。"""

import logging

from sellpilot.core.config import Settings
from sellpilot.services.embedding import EmbeddingService
from sellpilot.services.llm_service import LLMService
from sellpilot.services.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are SellPilot AI, a cross-border e-commerce operations assistant. "
    "Answer user questions based on the provided knowledge base content.\n\n"
    "Rules:\n"
    "1. Only answer based on the provided knowledge fragments. "
    "Do not fabricate information.\n"
    "2. If the knowledge base has no relevant information, say so honestly.\n"
    "3. Cite knowledge sources when answering "
    '(e.g. "According to user reviews...", "Based on the FAQ...").\n'
    "4. Answer in the same language as the user's question "
    "(Chinese questions → Chinese answers, English → English).\n"
    "5. Keep answers concise and professional."
)


class RAGService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._embedding: EmbeddingService | None = None
        self._vector_store: ChromaVectorStore | None = None
        self._llm: LLMService | None = None

    @property
    def embedding(self) -> EmbeddingService:
        if self._embedding is None:
            self._embedding = EmbeddingService()
        return self._embedding

    @property
    def vector_store(self) -> ChromaVectorStore:
        if self._vector_store is None:
            self._vector_store = ChromaVectorStore()
        return self._vector_store

    @property
    def llm(self) -> LLMService:
        if self._llm is None:
            self._llm = LLMService(self._settings)
        return self._llm

    def _build_context(self, fragments: list[dict]) -> str:
        parts: list[str] = []
        for i, frag in enumerate(fragments):
            meta = frag.get("metadata", {})
            cat = meta.get("category", "unknown")
            src = meta.get("source", "unknown")
            doc = frag.get("document", "")
            parts.append(
                f"[Fragment {i + 1}] Category: {cat} | Source: {src}\n{doc}"
            )
        return "\n\n".join(parts)

    def ask(
        self,
        question: str,
        *,
        top_k: int = 5,
        category: str | None = None,
        temperature: float = 0.3,
    ) -> dict:
        query_vec = self.embedding.encode_single(question)
        where = {"category": category} if category else None
        raw_results = self.vector_store.search(
            query_vec, top_k=top_k, where=where,
        )

        if not raw_results:
            return {
                "answer": "No relevant information found in the knowledge base.",
                "sources": [],
            }

        context = self._build_context(raw_results)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Knowledge base content:\n\n{context}\n\n"
                    f"User question: {question}"
                ),
            },
        ]
        answer = self.llm.chat(messages, temperature=temperature)

        sources = [
            {
                "score": round(r.get("score", 0), 4),
                "source_doc": r.get("metadata", {}).get("source", ""),
                "category": r.get("metadata", {}).get("category", ""),
                "fragment": (r.get("document", "") or "")[:300],
            }
            for r in raw_results
        ]
        return {"answer": answer, "sources": sources}
