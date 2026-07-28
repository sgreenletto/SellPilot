"""Embedding 服务 —— 封装 sentence-transformers 模型，支持批量向量化。"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# 默认模型：轻量、本地运行、中英文兼容
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


class EmbeddingService:
    """文本向量化服务。

    使用 sentence-transformers 在本地生成 embedding，无需外部 API。
    首次加载时自动下载模型（约 80MB），后续使用缓存。
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self._model_name = model_name
        self._model: Any = None

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model '%s' ...", self._model_name)
            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded. dim=%d", self.dim)
        return self._model

    @property
    def dim(self) -> int:
        try:
            return self.model.get_sentence_embedding_dimension()
        except AttributeError:
            return self.model.get_embedding_dimension()

    def encode(self, texts: list[str]) -> list[list[float]]:
        """对文本列表生成 embedding，返回 float 列表。"""
        if not texts:
            return []
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]
