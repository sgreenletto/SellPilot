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
    ContentExportResponse,
    ContentGenerateRequest,
    ContentGenerateResponse,
    ContentRegenerateFieldRequest,
    ContentRegenerateFieldResponse,
    ContentRestoreRequest,
    ContentVersionComparisonResponse,
    ContentVersionResponse,
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
    "/regenerate-field",
    response_model=ApiResponse[ContentRegenerateFieldResponse],
)
async def regenerate_field(
    payload: ContentRegenerateFieldRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ContentRegenerateFieldResponse]:
    result = await ContentGenerationService(session, settings).regenerate_field(payload, user.id)
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


@router.get(
    "/contents/{content_id}/versions/{version_id}",
    response_model=ApiResponse[ContentVersionResponse],
)
async def get_version(
    content_id: UUID,
    version_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ContentVersionResponse]:
    result = await ContentGenerationService(session, settings).get_version(
        content_id, version_id, user.id
    )
    return success_response(result, get_request_id(request))


@router.get(
    "/contents/{content_id}/compare",
    response_model=ApiResponse[ContentVersionComparisonResponse],
)
async def compare_versions(
    content_id: UUID,
    left_id: UUID,
    right_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ContentVersionComparisonResponse]:
    result = await ContentGenerationService(session, settings).compare_versions(
        content_id, left_id, right_id, user.id
    )
    return success_response(result, get_request_id(request))


@router.get(
    "/contents/{content_id}/versions/{version_id}/export",
    response_model=ApiResponse[ContentExportResponse],
)
async def export_version(
    content_id: UUID,
    version_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ContentExportResponse]:
    result = await ContentGenerationService(session, settings).export_version(
        content_id, version_id, user.id
    )
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
