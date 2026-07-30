"""知识库数据导入服务。"""

import asyncio
import csv
import hashlib
import logging
import shutil
import time
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import get_settings
from sellpilot.db.models.knowledge_base import KnowledgeChunk, KnowledgeDocument
from sellpilot.services.embedding import EmbeddingService
from sellpilot.services.llm_service import LLMService
from sellpilot.services.vector_store import DEFAULT_PERSIST_DIR as CHROMA_DIR
from sellpilot.services.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)

PRODUCTS_CSV = "products.csv"
REVIEWS_CSV = "reviews.csv"
MESSAGES_CSV = "customer_messages.csv"
SESSIONS_CSV = "customer_sessions.csv"

TRANSLATE_BATCH = 20  # 每批翻译条数


class KnowledgeIngestionError(ValueError):
    pass


class KnowledgeIngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure_assistant_demo_policy(
        self,
        source_path: Path,
        *,
        created_by: UUID | None = None,
    ) -> dict[str, object]:
        """Idempotently import the small, explicitly Mock Assistant policy document."""
        if created_by is None:
            created_by = await self._get_admin_id()

        if not await asyncio.to_thread(source_path.is_file):
            raise KnowledgeIngestionError(f"missing: {source_path}")
        content = (await asyncio.to_thread(source_path.read_text, encoding="utf-8")).strip()
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        source = "knowledge_mock/return-policy.md"
        document = await self.session.scalar(
            select(KnowledgeDocument).where(KnowledgeDocument.source == source)
        )
        if document is not None and document.checksum_sha256 == checksum:
            return {
                "inserted": 0,
                "skipped": 1,
                "document_id": str(document.id),
                "source": source,
            }
        if document is None:
            document = KnowledgeDocument(
                title="SellPilot Mock 店铺退货政策",
                file_type="markdown",
                file_size_bytes=len(content.encode("utf-8")),
                category="policy",
                status="indexed",
                source=source,
                checksum_sha256=checksum,
                chunk_count=1,
                metadata_json={"language": "zh-CN", "dataset": "assistant_demo_mock"},
                is_mock_data=True,
                created_by=created_by,
            )
            self.session.add(document)
            await self.session.flush()
            self.session.add(
                KnowledgeChunk(
                    document_id=document.id,
                    chunk_index=0,
                    content=content,
                    chunk_size=len(content),
                    embedding_status="not_required",
                    metadata_json={"language": "zh-CN"},
                    is_mock_data=True,
                )
            )
        else:
            document.file_size_bytes = len(content.encode("utf-8"))
            document.checksum_sha256 = checksum
            document.status = "indexed"
            chunks = list(
                (
                    await self.session.execute(
                        select(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id)
                    )
                ).scalars()
            )
            if chunks:
                chunks[0].content = content
                chunks[0].chunk_size = len(content)
            else:
                self.session.add(
                    KnowledgeChunk(
                        document_id=document.id,
                        chunk_index=0,
                        content=content,
                        chunk_size=len(content),
                        embedding_status="not_required",
                        metadata_json={"language": "zh-CN"},
                        is_mock_data=True,
                    )
                )
        await self.session.flush()
        return {
            "inserted": 1,
            "skipped": 0,
            "document_id": str(document.id),
            "source": source,
        }

    @staticmethod
    def _csv(data_dir: Path, name: str) -> list[dict]:
        p = data_dir / name
        if not p.is_file():
            raise KnowledgeIngestionError(f"missing: {name}")
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    # ---- 翻译 ----

    async def _translate_one(self, llm: LLMService, text: str) -> str:
        """逐条翻译为简体中文。"""
        try:
            resp = await llm.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a professional translator. "
                            "Translate the user's text into accurate, natural Simplified Chinese. "
                            "Preserve all factual information. "
                            "Return ONLY the Chinese text. "
                            "No explanations, notes, or quotation marks."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            result = resp.strip().strip('"').strip("'").strip()
            if result and not any("一" <= c <= "鿿" for c in result):
                logger.warning("Translation returned no Chinese chars, retrying")
                resp2 = await llm.chat(
                    [
                        {
                            "role": "user",
                            "content": (f"请将以下内容翻译成简体中文，只返回中文译文：\n\n{text}"),
                        }
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                )
                result = resp2.strip()
            return result
        except Exception as e:
            logger.warning("Translation failed: %s", e)
            return ""

    async def _translate_batch(self, llm: LLMService, texts: list[str], label: str) -> list[str]:
        """逐条翻译，带进度和限速。"""
        results: list[str] = []
        for i, t in enumerate(texts):
            zh = await self._translate_one(llm, t)
            results.append(zh if zh else t)
            if (i + 1) % 10 == 0:
                logger.info("Translated %d/%d %s", i + 1, len(texts), label)
                await asyncio.sleep(0.5)
        return results

    # ---- 文本格式化 ----

    @staticmethod
    def _prod(row: dict, zh: str = "") -> str:
        zh_line = f"Chinese: {zh}\n" if zh else ""
        return (
            f"[Product] {row.get('title', '')}\n"
            f"{zh_line}"
            f"Category: {row.get('category_name', '')}\n"
            f"Description: {row.get('description', '')}\n"
            f"Site: {row.get('site', '')} | "
            f"Price: {row.get('price', '')} {row.get('currency', '')} | "
            f"Sales: {row.get('sales_count', '')}"
        )

    @staticmethod
    def _rev(row: dict) -> str:
        zh = row.get("content_zh", "")
        zh_line = f"Chinese: {zh}\n" if zh else ""
        return (
            f"[User Review - {row.get('language', '')}]\n"
            f"Content: {row.get('content', '')}\n"
            f"{zh_line}"
            f"Issue: {row.get('issue_type', '')} | "
            f"Sentiment: {row.get('sentiment_hint', '')} | "
            f"Rating: {row.get('rating', '')}/5"
        )

    @staticmethod
    def _faq(
        q: str,
        a: str,
        lang: str,
        intent: str,
        risk: str,
        zh_q: str = "",
        zh_a: str = "",
    ) -> str:
        zh_line = ""
        if zh_q and zh_a:
            zh_line = f"Chinese Q: {zh_q}\nChinese A: {zh_a}\n"
        elif zh_q:
            zh_line = f"Chinese: {zh_q}\n"
        return (
            f"[CS Q&A - {lang}]\n"
            f"Buyer: {q}\n"
            f"Assistant: {a}\n"
            f"{zh_line}"
            f"Intent: {intent} | Risk: {risk}"
        )

    # ---- DB ----

    async def _get_admin_id(self) -> UUID:
        from sellpilot.db.models.user import User
        user = await self.session.scalar(
            select(User).where(User.username == "admin")
        )
        if user is None:
            raise KnowledgeIngestionError("admin user not found — run create-admin first")
        return user.id

    async def _make(self, title: str, content: str, cat: str, src: str, admin_id: UUID) -> KnowledgeDocument:
        doc = KnowledgeDocument(
            title=title,
            file_type="csv",
            file_size_bytes=len(content.encode()),
            category=cat,
            status="indexed",
            source=src,
            chunk_count=1,
            created_by=admin_id,
        )
        self.session.add(doc)
        await self.session.flush()
        self.session.add(
            KnowledgeChunk(
                document_id=doc.id,
                chunk_index=0,
                content=content,
                chunk_size=len(content),
            )
        )
        return doc

    async def _clear(self) -> int:
        c = (await self.session.execute(select(KnowledgeChunk.id))).scalars().all()
        await self.session.execute(delete(KnowledgeChunk))
        d = (await self.session.execute(select(KnowledgeDocument.id))).scalars().all()
        await self.session.execute(delete(KnowledgeDocument))
        await self.session.flush()
        return len(c) + len(d)

    # ---- 主流程 ----

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
            target = b_msgs if m.get("sender_type") == "buyer" else a_msgs
            target.setdefault(sid, []).append(m.get("content", ""))

        # ---- 翻译产品 & FAQ ----
        settings = get_settings()
        llm = LLMService(settings)
        logger.info("Translating products and FAQs to Chinese via %s ...", settings.llm_model)

        # 产品翻译
        prod_texts = [self._prod(row) for row in prods]
        prod_zh = await self._translate_batch(llm, prod_texts, "products")

        # FAQ 翻译（先清洗语言标签再翻译）
        import re

        def _clean(t: str) -> str:
            return re.sub(r"\[[A-Za-z ]+\]\s*", "", t).strip()

        faq_rows: list[tuple[str, str, str, str, str, str]] = []
        for sid in sorted(set(b_msgs) | set(a_msgs)):
            q = " ".join(b_msgs.get(sid, []))
            a = " ".join(a_msgs.get(sid, []))
            if not q or not a:
                continue
            s = smap.get(sid, {})
            faq_rows.append(
                (
                    sid,
                    q,
                    a,
                    s.get("language", ""),
                    s.get("intent", ""),
                    s.get("risk_level", ""),
                )
            )
        faq_qs_zh = await self._translate_batch(llm, [_clean(r[1]) for r in faq_rows], "FAQ questions")
        faq_as_zh = await self._translate_batch(llm, [_clean(r[2]) for r in faq_rows], "FAQ answers")

        # ---- 创建文档 ----
        admin_id = await self._get_admin_id()
        pc = rc = fc = 0
        for i, row in enumerate(prods):
            await self._make(
                row.get("title", ""),
                self._prod(row, prod_zh[i]),
                "product",
                f"products.csv#{row.get('product_id', '')}",
                admin_id,
            )
            pc += 1
        for row in revs:
            await self._make(
                f"Review {row.get('review_id', '')}",
                self._rev(row),
                "review",
                f"reviews.csv#{row.get('review_id', '')}",
                admin_id,
            )
            rc += 1
        for i, (sid, q, a, lang, intent, risk) in enumerate(faq_rows):
            await self._make(
                f"FAQ #{sid}",
                self._faq(q, a, lang, intent, risk, faq_qs_zh[i], faq_as_zh[i]),
                "faq",
                f"customer_messages.csv#{sid}",
                admin_id,
            )
            fc += 1

        await self.session.flush()
        total = pc + rc + fc

        # ---- Embedding + ChromaDB ----
        vs = ChromaVectorStore()
        es = EmbeddingService()
        off = 0
        while True:
            batch = list(
                (
                    await self.session.execute(
                        select(KnowledgeChunk)
                        .order_by(KnowledgeChunk.created_at)
                        .offset(off)
                        .limit(100)
                    )
                ).scalars()
            )
            if not batch:
                break
            embs = es.encode([c.content for c in batch])
            for chunk, emb in zip(batch, embs, strict=False):
                doc = await self.session.get(KnowledgeDocument, chunk.document_id)
                cat = doc.category if doc else "unknown"
                vs.upsert_chunks(
                    chunk.document_id,
                    [chunk.chunk_index],
                    [chunk.content],
                    [emb],
                    [
                        {
                            "document_id": str(chunk.document_id),
                            "chunk_index": chunk.chunk_index,
                            "category": cat,
                            "source": doc.source if doc else "",
                        }
                    ],
                )
                chunk.embedding_status = "embedded"
                chunk.chroma_id = f"{chunk.document_id}_{chunk.chunk_index}"
            await self.session.flush()
            off += 100
            logger.info("Embedded %d/%d", min(off, total), total)

        return {
            "cleared": cleared,
            "products": pc,
            "reviews": rc,
            "faq": fc,
            "total_documents": total,
            "total_chunks": total,
            "embedding_model": es._model_name,
            "embedding_dim": es.dim,
            "chroma_collection": vs._collection_name,
            "chroma_count": vs.count,
        }
