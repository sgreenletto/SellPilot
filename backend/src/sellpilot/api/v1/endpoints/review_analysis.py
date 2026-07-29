from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from sellpilot.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
)
from sellpilot.core.enums import SiteCode
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.review_analysis import (
    ReviewAnalysisCreatedResponse,
    ReviewAnalysisCreateRequest,
    ReviewAnalysisExportResponse,
    ReviewAnalysisResultResponse,
    ReviewEvidencePage,
    ReviewQuery,
    ReviewResponse,
)
from sellpilot.services.review_analysis import ReviewAnalysisService

router = APIRouter()


@router.get("/reviews", response_model=ApiResponse[list[ReviewResponse]])
async def list_reviews(
    request: Request,
    _user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    product_id: str,
    keyword: str | None = Query(default=None, min_length=1, max_length=100),
    site: SiteCode | None = None,
    language: str | None = None,
    min_rating: Annotated[int | None, Query(ge=1, le=5)] = None,
    max_rating: Annotated[int | None, Query(ge=1, le=5)] = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[list[ReviewResponse]]:
    data = await ReviewAnalysisService(session, settings).list_reviews(
        ReviewQuery(
            product_id=product_id,
            keyword=keyword,
            site=site,
            language=language,
            min_rating=min_rating,
            max_rating=max_rating,
            created_from=created_from,
            created_to=created_to,
            offset=offset,
            limit=limit,
        )
    )
    return success_response(data, get_request_id(request))


@router.post(
    "/analyses",
    response_model=ApiResponse[ReviewAnalysisCreatedResponse],
    status_code=202,
)
async def create_analysis(
    payload: ReviewAnalysisCreateRequest,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ReviewAnalysisCreatedResponse]:
    data = await ReviewAnalysisService(session, settings).create(payload, user.id)
    return success_response(data, get_request_id(request))


@router.post(
    "/analyses/{analysis_id}/run",
    response_model=ApiResponse[ReviewAnalysisResultResponse],
)
async def run_analysis(
    analysis_id: UUID,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ReviewAnalysisResultResponse]:
    data = await ReviewAnalysisService(session, settings).run(analysis_id, user.id)
    return success_response(data, get_request_id(request))


@router.get(
    "/analyses/{analysis_id}",
    response_model=ApiResponse[ReviewAnalysisResultResponse],
)
async def get_analysis(
    analysis_id: UUID,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ReviewAnalysisResultResponse]:
    data = await ReviewAnalysisService(session, settings).get(analysis_id, user.id)
    return success_response(data, get_request_id(request))


@router.get(
    "/analyses/{analysis_id}/export",
    response_model=ApiResponse[ReviewAnalysisExportResponse],
)
async def export_analysis(
    analysis_id: UUID,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[ReviewAnalysisExportResponse]:
    data = await ReviewAnalysisService(session, settings).export(analysis_id, user.id)
    return success_response(data, get_request_id(request))


@router.get(
    "/analyses/{analysis_id}/evidence",
    response_model=ApiResponse[ReviewEvidencePage],
)
async def list_evidence(
    analysis_id: UUID,
    request: Request,
    user: CurrentUserDependency,
    session: SessionDependency,
    settings: SettingsDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    evidence_type: str | None = None,
    label: str | None = None,
    sentiment: str | None = Query(default=None, pattern="^(positive|neutral|negative)$"),
) -> ApiResponse[ReviewEvidencePage]:
    data = await ReviewAnalysisService(session, settings).list_evidence(
        analysis_id,
        user.id,
        page=page,
        page_size=page_size,
        evidence_type=evidence_type,
        label=label,
        sentiment=sentiment,
    )
    return success_response(data, get_request_id(request))
