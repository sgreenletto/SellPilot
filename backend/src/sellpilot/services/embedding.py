"""Embedding 服务 —— 启动时即加载模型，避免首次请求阻塞。"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

# 启动时即加载，不延迟到首次 API 调用
_model: Any = None
_model_name: str = DEFAULT_MODEL_NAME


def _load_model() -> Any:
    from sentence_transformers import SentenceTransformer

    # 禁用 HF Hub 网络请求，只用本地缓存
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    logger.info("Loading embedding model '%s' ...", _model_name)
    m = SentenceTransformer(_model_name, local_files_only=True)
    logger.info("Embedding model ready. dim=%d", m.get_sentence_embedding_dimension())
    return m


def get_model() -> Any:
    global _model
    if _model is None:
        _model = _load_model()
    return _model


def encode(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    embeddings = get_model().encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def encode_single(text: str) -> list[float]:
    return encode([text])[0]


def get_dim() -> int:
    return get_model().get_sentence_embedding_dimension()


class EmbeddingService:
    """兼容旧接口的 wrapper。"""

    def __init__(self) -> None:
        self._model_name = _model_name
        get_model()  # eager load

    @property
    def dim(self) -> int:
        return get_dim()

    def encode(self, texts: list[str]) -> list[list[float]]:
        return encode(texts)

    def encode_single(self, text: str) -> list[float]:
        return encode_single(text)
