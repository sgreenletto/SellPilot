"""ChromaDB 向量存储服务。

封装 ChromaDB 客户端，提供 collection 管理、文档插入、删除和相似度搜索。
持久化到磁盘（backend/chroma_data/），与业务数据库独立。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "sellpilot_knowledge"
DEFAULT_PERSIST_DIR = Path(__file__).resolve().parents[3] / "chroma_data"


class ChromaVectorStore:
    """ChromaDB 向量存储。

    每个 knowledge_chunk 保存为一个 Chroma 文档：
      - id: chroma_id = f"{document_id}_{chunk_index}"
      - embedding: 由 EmbeddingService 生成
      - document: chunk.content
      - metadata: {document_id, category, source, chunk_index}
    """

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION,
        persist_dir: Path | str = DEFAULT_PERSIST_DIR,
    ) -> None:
        import chromadb
        from chromadb.config import Settings

        self._persist_dir = Path(persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._collection_name = collection_name

        self._client = chromadb.PersistentClient(
            path=str(self._persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": "SellPilot RAG knowledge base",
                "hnsw:space": "cosine",
            },
        )
        logger.info(
            "ChromaDB ready: collection='%s' dir='%s' count=%d",
            collection_name,
            self._persist_dir,
            self._collection.count(),
        )

    @property
    def collection(self) -> Any:
        return self._collection

    @property
    def count(self) -> int:
        return self._collection.count()

    # ---- 写入 ----

    def upsert_chunks(
        self,
        document_id: UUID,
        chunk_indices: list[int],
        texts: list[str],
        embeddings: list[list[float]],
        metadata_list: list[dict] | None = None,
    ) -> None:
        """批量插入或更新 chunk 向量。"""
        if not texts:
            return
        ids = [f"{document_id}_{idx}" for idx in chunk_indices]
        metadatas = metadata_list or [{} for _ in texts]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.debug("Upserted %d chunks for doc %s", len(texts), document_id)

    # ---- 删除 ----

    def delete_by_document(self, document_id: UUID) -> int:
        """删除某个文档的所有 chunk 向量。返回删除数量。"""
        deleted = 0
        while True:
            existing = self._collection.get(
                where={"document_id": str(document_id)},
                limit=1000,
                include=[],
            )
            ids_to_delete = existing.get("ids", [])
            if not ids_to_delete:
                break
            self._collection.delete(ids=ids_to_delete)
            deleted += len(ids_to_delete)
        logger.debug("Deleted %d vectors for doc %s", deleted, document_id)
        return deleted

    def clear_all(self) -> int:
        """清空整个 collection。分批处理，避免 ChromaDB get() 默认限制。"""
        batch_size = 1000
        deleted = 0
        while True:
            result = self._collection.get(limit=batch_size, include=[])
            ids = result.get("ids", [])
            if not ids:
                break
            self._collection.delete(ids=ids)
            deleted += len(ids)
        return deleted

    # ---- 检索 ----

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """相似度搜索，返回 Top-K 结果。

        每个结果: {id, document, score, metadata}
        """
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        items: list[dict] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, chroma_id in enumerate(ids):
            score = 1.0 - distances[i] if i < len(distances) else 0.0
            items.append(
                {
                    "chroma_id": chroma_id,
                    "document": documents[i] if i < len(documents) else "",
                    "score": max(0.0, min(1.0, score)),
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                }
            )
        return items
