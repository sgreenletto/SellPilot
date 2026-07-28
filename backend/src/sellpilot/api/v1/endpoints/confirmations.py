from uuid import UUID

from fastapi import APIRouter, Query, Request

from sellpilot.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
)
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, PageResult, success_response
from sellpilot.schemas.confirmation import ConfirmationTaskResponse
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.tools.runtime import build_confirmation_service

router = APIRouter()


@router.get("", response_model=ApiResponse[PageResult[ConfirmationTaskResponse]])
async def list_confirmations(
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[PageResult[ConfirmationTaskResponse]]:
    confirmations, total = await ConfirmationService(session).list(page, page_size)
    result = PageResult[ConfirmationTaskResponse](
        items=[
            ConfirmationTaskResponse.model_validate(confirmation) for confirmation in confirmations
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
    return success_response(result, get_request_id(request))


@router.get("/{confirmation_id}", response_model=ApiResponse[ConfirmationTaskResponse])
async def get_confirmation(
    confirmation_id: UUID,
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await ConfirmationService(session).get(confirmation_id)
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation),
        get_request_id(request),
    )


@router.post(
    "/{confirmation_id}/confirm",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def confirm_confirmation(
    confirmation_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await build_confirmation_service(
        request.app.state.tool_registry,
        session,
        settings,
    ).confirm(confirmation_id, current_user.id)
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation),
        get_request_id(request),
    )


@router.post(
    "/{confirmation_id}/cancel",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def cancel_confirmation(
    confirmation_id: UUID,
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await ConfirmationService(session).cancel(confirmation_id)
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation),
        get_request_id(request),
    )
