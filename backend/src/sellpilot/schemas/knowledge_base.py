from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from sellpilot.schemas.common import ContractModel, PaginationParams

# ---- Enums (wire-value strings matching DB) ----


class KnowledgeDocumentStatus:
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class KnowledgeChunkEmbeddingStatus:
    PENDING = "pending"
    EMBEDDED = "embedded"
    FAILED = "failed"


class KnowledgeFileType:
    PDF = "pdf"
    MARKDOWN = "markdown"
    TXT = "txt"


class KnowledgeCategory:
    PRODUCT = "product"
    FAQ = "faq"
    POLICY = "policy"
    LOGISTICS = "logistics"


# ---- Document Schemas ----


class KnowledgeDocumentCreate(ContractModel):
    title: str = Field(min_length=1, max_length=300)
    file_type: str = Field(min_length=1, max_length=16)
    file_size_bytes: int = Field(ge=0, default=0)
    category: str = Field(min_length=1, max_length=64)
    source: str | None = Field(default=None, max_length=200)
    metadata_json: dict = Field(default_factory=dict)


class KnowledgeDocumentUpdate(ContractModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    source: str | None = Field(default=None, max_length=200)
    metadata_json: dict | None = None


class KnowledgeDocumentResponse(ContractModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    file_type: str
    file_size_bytes: int
    category: str
    status: str
    file_path: str | None = None
    checksum_sha256: str | None = None
    chunk_count: int = 0
    error_message: str | None = None
    source: str | None = None
    metadata_json: dict = Field(default_factory=dict)
    is_mock_data: bool = False
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentListParams(PaginationParams):
    category: str | None = Field(default=None, min_length=1, max_length=64)
    status: str | None = Field(default=None, min_length=1, max_length=32)


# ---- Chunk Schemas ----


class KnowledgeChunkResponse(ContractModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    chunk_size: int = 0
    embedding_status: str
    chroma_id: str | None = None
    metadata_json: dict = Field(default_factory=dict)
    is_mock_data: bool = False
    created_at: datetime


class KnowledgeChunkListParams(PaginationParams):
    document_id: UUID | None = None
    embedding_status: str | None = Field(default=None, min_length=1, max_length=32)


# ---- Retrieval Schemas (Phase 2 使用，先定义结构) ----


class KnowledgeRetrievalRequest(ContractModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    category: str | None = Field(default=None, min_length=1, max_length=64)


class KnowledgeRetrievalItem(ContractModel):
    fragment: str
    score: float = Field(ge=0.0, le=1.0)
    source_doc: str
    document_id: UUID
    chunk_index: int


# ---- RAG Q&A ----

class RAGQuestionRequest(ContractModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    category: str | None = Field(default=None, min_length=1, max_length=64)


class RAGSourceItem(ContractModel):
    score: float
    source_doc: str = ""
    category: str = ""
    fragment: str = ""


class RAGAnswerResponse(ContractModel):
    answer: str
    sources: list[RAGSourceItem] = Field(default_factory=list)
