"""知识库 API —— 检索 + 文档管理。

所有接口位于 /api/v1/knowledge，需要 Bearer Token。
"""

from uuid import UUID

from fastapi import APIRouter, Query, Request

from sellpilot.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
)
from sellpilot.core.exceptions import ResourceNotFoundError
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, PageResult, success_response
from sellpilot.schemas.knowledge_base import (
    KnowledgeChunkResponse,
    KnowledgeDocumentResponse,
    KnowledgeRetrievalItem,
    KnowledgeRetrievalRequest,
    RAGAnswerResponse,
    RAGQuestionRequest,
)
from sellpilot.services.knowledge_base import KnowledgeBaseService
from sellpilot.services.rag_service import RAGService

router = APIRouter()


# ---- 检索 ----


@router.post("/retrieve", response_model=ApiResponse[list[KnowledgeRetrievalItem]])
async def retrieve_knowledge(
    payload: KnowledgeRetrievalRequest,
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[list[KnowledgeRetrievalItem]]:
    """从现有 PostgreSQL 知识记录执行有界检索并返回来源片段。"""
    raw_results = await RAGService(settings, session).retrieve(
        payload.query,
        top_k=payload.top_k,
        category=payload.category,
    )
    items = [KnowledgeRetrievalItem.model_validate(item) for item in raw_results]
    return success_response(items, get_request_id(request))


# ---- 文档 CRUD ----


@router.get("/documents", response_model=ApiResponse[PageResult[KnowledgeDocumentResponse]])
async def list_documents(
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> ApiResponse[PageResult[KnowledgeDocumentResponse]]:
    """分页查询知识文档列表，支持 category/status 筛选。"""
    service = KnowledgeBaseService(session, settings)
    docs, total = await service.list_documents(page, page_size, category=category, status=status)
    items = [KnowledgeDocumentResponse.model_validate(d) for d in docs]
    return success_response(
        PageResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        ),
        get_request_id(request),
    )


@router.get(
    "/documents/{document_id}",
    response_model=ApiResponse[KnowledgeDocumentResponse],
)
async def get_document(
    document_id: UUID,
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[KnowledgeDocumentResponse]:
    """获取单个知识文档详情。"""
    service = KnowledgeBaseService(session, settings)
    doc = await service.get_document(document_id)
    if doc is None:
        raise ResourceNotFoundError("Knowledge document not found")
    return success_response(KnowledgeDocumentResponse.model_validate(doc), get_request_id(request))


@router.delete("/documents/{document_id}", response_model=ApiResponse[dict])
async def delete_document(
    document_id: UUID,
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[dict]:
    """删除知识文档及其关联的 PostgreSQL chunk 记录。"""
    service = KnowledgeBaseService(session, settings)
    ok = await service.delete_document(document_id)
    if not ok:
        raise ResourceNotFoundError("Knowledge document not found")
    return success_response(
        {"deleted": True, "document_id": str(document_id)},
        get_request_id(request),
    )


# ---- Chunk 查询 ----


@router.get(
    "/documents/{document_id}/chunks",
    response_model=ApiResponse[PageResult[KnowledgeChunkResponse]],
)
async def list_chunks(
    document_id: UUID,
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[PageResult[KnowledgeChunkResponse]]:
    """查询某个文档下的所有文本切块。"""
    service = KnowledgeBaseService(session, settings)
    chunks, total = await service.list_chunks(document_id, page, page_size)
    items = [KnowledgeChunkResponse.model_validate(c) for c in chunks]
    return success_response(
        PageResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        ),
        get_request_id(request),
    )


# ---- RAG Q&A ----


@router.post("/qa", response_model=ApiResponse[RAGAnswerResponse])
async def rag_qa(
    payload: RAGQuestionRequest,
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[RAGAnswerResponse]:
    """RAG 大模型问答。"""
    rag = RAGService(settings, session)
    result = await rag.ask(
        question=payload.question,
        top_k=payload.top_k,
        category=payload.category,
    )
    return success_response(
        RAGAnswerResponse(**result),
        get_request_id(request),
    )
