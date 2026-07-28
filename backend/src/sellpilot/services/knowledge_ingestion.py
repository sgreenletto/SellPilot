"""知识库数据导入服务。"""

import csv
import logging
import shutil
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.knowledge_base import KnowledgeChunk, KnowledgeDocument
from sellpilot.services.embedding import EmbeddingService
from sellpilot.services.vector_store import ChromaVectorStore, DEFAULT_PERSIST_DIR as CHROMA_DIR

logger = logging.getLogger(__name__)

_ADMIN = UUID("d5f72327-fc9b-4da5-b51a-7a7a6329e5f7")
PRODUCTS_CSV = "products.csv"
REVIEWS_CSV = "reviews.csv"
MESSAGES_CSV = "customer_messages.csv"
SESSIONS_CSV = "customer_sessions.csv"


class KnowledgeIngestionError(ValueError):
    pass


class KnowledgeIngestionService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _csv(data_dir: Path, name: str) -> list[dict]:
        p = data_dir / name
        if not p.is_file():
            raise KnowledgeIngestionError(f"missing: {name}")
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    # ---- emb 文本：不含假中文翻译 ----

    @staticmethod
    def _prod(row: dict) -> str:
        return (
            f"[Product] {row.get('title','')}\n"
            f"Category: {row.get('category_name','')}\n"
            f"Description: {row.get('description','')}\n"
            f"Site: {row.get('site','')} | Price: {row.get('price','')} {row.get('currency','')} | Sales: {row.get('sales_count','')}"
        )

    @staticmethod
    def _rev(row: dict) -> str:
        zh = row.get('content_zh', '')
        zh_line = f"Chinese: {zh}\n" if zh else ""
        return (
            f"[User Review - {row.get('language','')}]\n"
            f"Content: {row.get('content','')}\n"
            f"{zh_line}"
            f"Issue: {row.get('issue_type','')} | Sentiment: {row.get('sentiment_hint','')} | Rating: {row.get('rating','')}/5"
        )

    @staticmethod
    def _faq(q: str, a: str, lang: str, intent: str, risk: str) -> str:
        return (
            f"[CS Q&A - {lang}]\n"
            f"Buyer: {q}\n"
            f"Assistant: {a}\n"
            f"Intent: {intent} | Risk: {risk}"
        )

    async def _make(self, title: str, content: str, cat: str, src: str) -> KnowledgeDocument:
        doc = KnowledgeDocument(
            title=title, file_type="csv", file_size_bytes=len(content.encode()),
            category=cat, status="indexed", source=src, chunk_count=1, created_by=_ADMIN,
        )
        self.session.add(doc)
        await self.session.flush()
        self.session.add(KnowledgeChunk(document_id=doc.id, chunk_index=0, content=content, chunk_size=len(content)))
        return doc

    async def _clear(self) -> int:
        c = (await self.session.execute(select(KnowledgeChunk.id))).scalars().all()
        await self.session.execute(delete(KnowledgeChunk))
        d = (await self.session.execute(select(KnowledgeDocument.id))).scalars().all()
        await self.session.execute(delete(KnowledgeDocument))
        await self.session.flush()
        return len(c) + len(d)

    async def import_package(self, data_dir: Path) -> dict:
        cleared = await self._clear()
        if CHROMA_DIR.exists():
            shutil.rmtree(str(CHROMA_DIR), ignore_errors=True)

        prods = self._csv(data_dir, PRODUCTS_CSV)
        revs = self._csv(data_dir, REVIEWS_CSV)
        msgs = self._csv(data_dir, MESSAGES_CSV)
        sess = self._csv(data_dir, SESSIONS_CSV)

        smap = {s["session_id"]: s for s in sess if s.get("session_id")}
        b_msgs: dict[str, list[str]] = {}
        a_msgs: dict[str, list[str]] = {}
        for m in msgs:
            sid = m.get("session_id", "")
            (b_msgs if m.get("sender_type") == "buyer" else a_msgs).setdefault(sid, []).append(m.get("content", ""))

        pc = rc = fc = 0
        for row in prods:
            await self._make(row.get("title", ""), self._prod(row), "product", f"products.csv#{row.get('product_id','')}")
            pc += 1
        for row in revs:
            await self._make(f"Review {row.get('review_id','')}", self._rev(row), "review", f"reviews.csv#{row.get('review_id','')}")
            rc += 1
        for sid in sorted(set(b_msgs) | set(a_msgs)):
            q = " ".join(b_msgs.get(sid, []))
            a = " ".join(a_msgs.get(sid, []))
            if not q or not a:
                continue
            s = smap.get(sid, {})
            await self._make(f"FAQ #{sid}", self._faq(q, a, s.get("language", ""), s.get("intent", ""), s.get("risk_level", "")), "faq", f"customer_messages.csv#{sid}")
            fc += 1

        await self.session.flush()
        total = pc + rc + fc

        vs = ChromaVectorStore()
        es = EmbeddingService()
        off = 0
        while True:
            batch = list((await self.session.execute(select(KnowledgeChunk).order_by(KnowledgeChunk.created_at).offset(off).limit(100))).scalars())
            if not batch:
                break
            embs = es.encode([c.content for c in batch])
            for chunk, emb in zip(batch, embs):
                doc = await self.session.get(KnowledgeDocument, chunk.document_id)
                cat = doc.category if doc else "unknown"
                vs.upsert_chunks(chunk.document_id, [chunk.chunk_index], [chunk.content], [emb],
                    [{"document_id": str(chunk.document_id), "chunk_index": chunk.chunk_index, "category": cat, "source": doc.source if doc else ""}])
                chunk.embedding_status = "embedded"
                chunk.chroma_id = f"{chunk.document_id}_{chunk.chunk_index}"
            await self.session.flush()
            off += 100
            logger.info("Embedded %d/%d", min(off, total), total)

        return {"cleared": cleared, "products": pc, "reviews": rc, "faq": fc, "total_documents": total, "total_chunks": total, "embedding_model": es._model_name, "embedding_dim": es.dim, "chroma_collection": vs._collection_name, "chroma_count": vs.count}
