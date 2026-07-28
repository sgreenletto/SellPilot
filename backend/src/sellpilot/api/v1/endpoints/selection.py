from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from sellpilot.api.dependencies import CurrentUserDependency, SessionDependency
from sellpilot.core.enums import SiteCode
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.selection import (
    SelectionAnalysisRequest,
    SelectionAnalysisResponse,
    SelectionCandidateQuery,
    SelectionCandidateResponse,
    SelectionExportResponse,
    SelectionResultResponse,
    SelectionSortField,
    SelectionTaskResponse,
)
from sellpilot.services.selection import SelectionService

router = APIRouter()


@router.get("/candidates", response_model=ApiResponse[list[SelectionCandidateResponse]])
async def list_candidates(
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    site: SiteCode,
    category_id: str | None = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(gt=0)] = None,
    sort_by: SelectionSortField = "sales_count",
    descending: bool = True,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> ApiResponse[list[SelectionCandidateResponse]]:
    query = SelectionCandidateQuery(
        site=site,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        descending=descending,
        offset=offset,
        limit=limit,
    )
    data = await SelectionService(session).list_candidates(query)
    return success_response(data, get_request_id(request))


@router.post("/analyses", response_model=ApiResponse[SelectionAnalysisResponse])
async def create_analysis(
    payload: SelectionAnalysisRequest,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
) -> ApiResponse[SelectionAnalysisResponse]:
    data = await SelectionService(session).analyze(payload, user.id)
    return success_response(data, get_request_id(request))


@router.get("/analyses/{task_id}", response_model=ApiResponse[SelectionTaskResponse])
async def get_analysis(
    task_id: UUID,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
) -> ApiResponse[SelectionTaskResponse]:
    data = await SelectionService(session).get_task(task_id, user.id)
    return success_response(data, get_request_id(request))


@router.get(
    "/analyses/{task_id}/compare",
    response_model=ApiResponse[list[SelectionResultResponse]],
)
async def compare_products(
    task_id: UUID,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    product_id: Annotated[list[str], Query(min_length=2, max_length=10)],
) -> ApiResponse[list[SelectionResultResponse]]:
    data = await SelectionService(session).compare(task_id, product_id, user.id)
    return success_response(data, get_request_id(request))


@router.get(
    "/analyses/{task_id}/export",
    response_model=ApiResponse[SelectionExportResponse],
)
async def export_analysis(
    task_id: UUID,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
) -> ApiResponse[SelectionExportResponse]:
    data = await SelectionService(session).export(task_id, user.id)
    return success_response(data, get_request_id(request))
