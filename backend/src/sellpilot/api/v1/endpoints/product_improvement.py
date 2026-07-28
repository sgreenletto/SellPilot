from uuid import UUID

from fastapi import APIRouter, Request

from sellpilot.api.dependencies import CurrentUserDependency, SessionDependency, SettingsDependency
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.confirmation import ConfirmationTaskResponse
from sellpilot.schemas.product_improvement import (
    ImprovementDraftRequest,
    ImprovementGenerateRequest,
    ImprovementReportResponse,
    ImprovementSuggestionResponse,
    SuggestionUpdateRequest,
)
from sellpilot.services.product_improvement import ProductImprovementService

router = APIRouter()


@router.post("/reports", response_model=ApiResponse[ImprovementReportResponse])
async def generate_report(
    payload: ImprovementGenerateRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ImprovementReportResponse]:
    result = await ProductImprovementService(session, settings).generate(
        payload.analysis_id, user.id
    )
    return success_response(result, get_request_id(request))


@router.get("/reports/{report_id}", response_model=ApiResponse[ImprovementReportResponse])
async def get_report(
    report_id: UUID,
    request: Request,
    session: SessionDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ImprovementReportResponse]:
    result = await ProductImprovementService(session).get_report(report_id, user.id)
    return success_response(result, get_request_id(request))


@router.patch(
    "/suggestions/{suggestion_id}",
    response_model=ApiResponse[ImprovementSuggestionResponse],
)
async def update_suggestion(
    suggestion_id: UUID,
    payload: SuggestionUpdateRequest,
    request: Request,
    session: SessionDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ImprovementSuggestionResponse]:
    result = await ProductImprovementService(session).update_suggestion(
        suggestion_id, payload, user.id
    )
    return success_response(result, get_request_id(request))


@router.get("/reports/{report_id}/export", response_model=ApiResponse[dict])
async def export_report(
    report_id: UUID,
    request: Request,
    session: SessionDependency,
    user: CurrentUserDependency,
) -> ApiResponse[dict]:
    result = await ProductImprovementService(session).export(report_id, user.id)
    return success_response(result, get_request_id(request))


@router.post(
    "/reports/{report_id}/draft-confirmations",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_draft(
    report_id: UUID,
    payload: ImprovementDraftRequest,
    request: Request,
    session: SessionDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    result = await ProductImprovementService(session).request_draft(report_id, payload, user.id)
    return success_response(
        ConfirmationTaskResponse.model_validate(result), get_request_id(request)
    )
