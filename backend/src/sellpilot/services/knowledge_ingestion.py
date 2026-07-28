"""知识库数据导入服务。

从 data/demo/shopee_mock/ 的三个 CSV 读取模拟数据，
转换为统一的知识文档 + 文本切块格式，写入 knowledge_documents 和 knowledge_chunks 表，
并生成 embedding 存入 ChromaDB。
"""

import csv
import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.knowledge_base import KnowledgeChunk, KnowledgeDocument
from sellpilot.services.embedding import EmbeddingService
from sellpilot.services.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)

# 默认管理员的 UUID — 与 CLI create_admin 创建的用户一致
_ADMIN_USER_ID = UUID("d5f72327-fc9b-4da5-b51a-7a7a6329e5f7")

PRODUCTS_CSV = "products.csv"
REVIEWS_CSV = "reviews.csv"
MESSAGES_CSV = "customer_messages.csv"
SESSIONS_CSV = "customer_sessions.csv"


class KnowledgeIngestionError(ValueError):
    pass


class KnowledgeIngestionService:
    """读取 CSV 并将数据导入知识库。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- CSV 读取 ----

    @staticmethod
    def _read_csv(data_dir: Path, filename: str) -> list[dict]:
        path = data_dir / filename
        if not path.is_file():
            raise KnowledgeIngestionError(f"missing data file: {filename}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    # ---- 文本格式化 ----

    @staticmethod
    def _format_product(row: dict) -> str:
        return (
            f"商品名称: {row.get('title', '')}\n"
            f"类目: {row.get('category_name', '')}\n"
            f"描述: {row.get('description', '')}\n"
            f"站点: {row.get('site', '')}  |  "
            f"价格: {row.get('price', '')} {row.get('currency', '')}  |  "
            f"销量: {row.get('sales_count', '')}  |  "
            f"评分: {row.get('rating', '')}/5"
        )

    @staticmethod
    def _format_review(row: dict) -> str:
        language = row.get("language", "")
        return (
            f"[用户评论 - {language}]\n"
            f"原文: {row.get('content', '')}\n"
            f"中文翻译: {row.get('content_zh', '')}\n"
            f"情感: {row.get('sentiment_hint', '')}  |  "
            f"问题类型: {row.get('issue_type', '')}  |  "
            f"评分: {row.get('rating', '')}/5"
        )

    @staticmethod
    def _format_faq(
        question: str,
        answer: str,
        language: str,
        intent: str,
        risk_level: str,
    ) -> str:
        return (
            f"[客服问答 - {language}]\n"
            f"买家问题: {question}\n"
            f"客服回答: {answer}\n"
            f"意图: {intent}  |  风险级别: {risk_level}"
        )

    # ---- 文档 + 切块创建 ----

    async def _create_document_with_chunk(
        self,
        title: str,
        content: str,
        file_type: str,
        category: str,
        source: str,
        *,
        created_by: UUID | None = None,
    ) -> KnowledgeDocument:
        doc = KnowledgeDocument(
            title=title,
            file_type=file_type,
            file_size_bytes=len(content.encode("utf-8")),
            category=category,
            status="indexed",  # CSV 导入直接视为已索引
            source=source,
            chunk_count=1,
            created_by=created_by or _ADMIN_USER_ID,
        )
        self.session.add(doc)
        await self.session.flush()

        chunk = KnowledgeChunk(
            document_id=doc.id,
            chunk_index=0,
            content=content,
            chunk_size=len(content),
            embedding_status="pending",
        )
        self.session.add(chunk)
        return doc

    # ---- 核心导入流程 ----

    async def _clear_existing(self) -> int:
        """清空已有知识库数据，返回删除的文档数。"""
        count_result = await self.session.execute(select(KnowledgeDocument.id))
        count = len(list(count_result.scalars()))
        await self.session.execute(delete(KnowledgeDocument))
        await self.session.flush()
        return count

    async def import_package(self, data_dir: Path) -> dict:
        """从 data_dir 读取 3 个 CSV 并导入知识库，返回统计摘要。"""
        # 1. 清空
        cleared = await self._clear_existing()

        # 2. 读取 CSV
        products = self._read_csv(data_dir, PRODUCTS_CSV)
        reviews = self._read_csv(data_dir, REVIEWS_CSV)
        messages = self._read_csv(data_dir, MESSAGES_CSV)
        sessions = self._read_csv(data_dir, SESSIONS_CSV)

        # 3. 建立 session_id → session 映射（获取 intent + risk_level）
        session_map: dict[str, dict] = {}
        for s in sessions:
            session_map[s.get("session_id", "")] = s

        # 4. 构建 FAQ Q&A 对：按 session_id 分组消息
        buyer_msgs: dict[str, list[str]] = {}
        assistant_msgs: dict[str, list[str]] = {}
        for m in messages:
            sid = m.get("session_id", "")
            if m.get("sender_type", "") == "buyer":
                buyer_msgs.setdefault(sid, []).append(m.get("content", ""))
            else:
                assistant_msgs.setdefault(sid, []).append(m.get("content", ""))

        # 5. 导入商品
        product_count = 0
        for row in products:
            title = row.get("title", f"Product {row.get('product_id', '')}")
            content = self._format_product(row)
            await self._create_document_with_chunk(
                title=title,
                content=content,
                file_type="csv",
                category="product",
                source=f"products.csv#{row.get('product_id', '')}",
            )
            product_count += 1

        # 6. 导入评论
        review_count = 0
        for row in reviews:
            title = f"评论 {row.get('review_id', '')} (商品 {row.get('product_id', '')})"
            content = self._format_review(row)
            await self._create_document_with_chunk(
                title=title,
                content=content,
                file_type="csv",
                category="review",
                source=f"reviews.csv#{row.get('review_id', '')}",
            )
            review_count += 1

        # 7. 导入 FAQ 问答对
        faq_count = 0
        processed_sids: set[str] = set()
        for sid in sorted(set(buyer_msgs.keys()) | set(assistant_msgs.keys())):
            if sid in processed_sids:
                continue
            processed_sids.add(sid)
            question = " ".join(buyer_msgs.get(sid, []))
            answer = " ".join(assistant_msgs.get(sid, []))
            if not question or not answer:
                # 跳过不完整的对话
                continue
            session = session_map.get(sid, {})
            language = session.get("language", messages[0].get("language", "")) if messages else ""
            content = self._format_faq(
                question=question,
                answer=answer,
                language=language,
                intent=session.get("intent", ""),
                risk_level=session.get("risk_level", ""),
            )
            await self._create_document_with_chunk(
                title=f"客服问答 #{sid}",
                content=content,
                file_type="csv",
                category="faq",
                source=f"customer_messages.csv#{sid}",
            )
            faq_count += 1

        await self.session.flush()

        # ---- 向量化阶段：批量 embedding + ChromaDB ----
        embed_count = 0
        vector_store = ChromaVectorStore()
        vector_store.clear_all()

        embedding_service = EmbeddingService()
        batch_size = 100

        # 分批读取所有 chunk → embedding → ChromaDB
        offset = 0
        while True:
            batch_result = await self.session.execute(
                select(KnowledgeChunk)
                .order_by(KnowledgeChunk.created_at)
                .offset(offset)
                .limit(batch_size)
            )
            batch = list(batch_result.scalars())
            if not batch:
                break

            texts = [c.content for c in batch]
            embeddings = embedding_service.encode(texts)

            for chunk, embedding in zip(batch, embeddings, strict=True):
                # 关联文档获取 category
                doc = await self.session.get(KnowledgeDocument, chunk.document_id)
                category = doc.category if doc else "unknown"
                vector_store.upsert_chunks(
                    document_id=chunk.document_id,
                    chunk_indices=[chunk.chunk_index],
                    texts=[chunk.content],
                    embeddings=[embedding],
                    metadata_list=[
                        {
                            "document_id": str(chunk.document_id),
                            "chunk_index": chunk.chunk_index,
                            "category": category,
                            "source": doc.source if doc else "",
                        }
                    ],
                )
                chunk.embedding_status = "embedded"
                chunk.chroma_id = f"{chunk.document_id}_{chunk.chunk_index}"

            await self.session.flush()
            embed_count += len(batch)
            offset += batch_size
            logger.info(
                "Embedded %d/%d chunks",
                embed_count,
                product_count + review_count + faq_count,
            )

        return {
            "cleared": cleared,
            "products": product_count,
            "reviews": review_count,
            "faq": faq_count,
            "total_documents": product_count + review_count + faq_count,
            "total_chunks": product_count + review_count + faq_count,
            "embedding_model": embedding_service._model_name,
            "embedding_dim": embedding_service.dim,
            "chroma_collection": vector_store._collection_name,
            "chroma_count": vector_store.count,
        }
