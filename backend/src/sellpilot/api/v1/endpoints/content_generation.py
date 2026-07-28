from uuid import UUID

from fastapi import APIRouter, Request

from sellpilot.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
)
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.confirmation import ConfirmationTaskResponse
from sellpilot.schemas.content_generation import (
    ContentDraftRequest,
    ContentGenerateRequest,
    ContentGenerateResponse,
    ContentRestoreRequest,
    ContentVersionsResponse,
)
from sellpilot.services.content_generation import ContentGenerationService

router = APIRouter()


@router.post("/generate", response_model=ApiResponse[ContentGenerateResponse])
async def generate(
    payload: ContentGenerateRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ContentGenerateResponse]:
    result = await ContentGenerationService(session, settings).generate(payload, user.id)
    return success_response(result, get_request_id(request))


@router.post(
    "/draft-confirmations",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_draft(
    payload: ContentDraftRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    result = await ContentGenerationService(session, settings).request_draft(payload, user.id)
    return success_response(
        ConfirmationTaskResponse.model_validate(result), get_request_id(request)
    )


@router.get(
    "/contents/{content_id}/versions",
    response_model=ApiResponse[ContentVersionsResponse],
)
async def list_versions(
    content_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ContentVersionsResponse]:
    result = await ContentGenerationService(session, settings).list_versions(content_id, user.id)
    return success_response(result, get_request_id(request))


@router.post(
    "/contents/{content_id}/restore-confirmations",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_restore(
    content_id: UUID,
    payload: ContentRestoreRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    result = await ContentGenerationService(session, settings).request_restore(
        content_id, payload, user.id
    )
    return success_response(
        ConfirmationTaskResponse.model_validate(result), get_request_id(request)
    )
