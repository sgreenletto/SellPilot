from uuid import UUID

from fastapi import APIRouter, Request

from sellpilot.api.dependencies import CurrentUserDependency, SessionDependency, SettingsDependency
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.ai_management import (
    MemberThreeEvaluationSummary,
    ModelInvocationSummary,
    ModelRuntimeSummary,
    PromptStatusChangeRequest,
    PromptTemplateSummary,
    PromptVersionChangeRequest,
    PromptVersionSummary,
)
from sellpilot.schemas.confirmation import ConfirmationTaskResponse
from sellpilot.services.ai_management import AIManagementService

router = APIRouter()


@router.get("/prompts", response_model=ApiResponse[list[PromptTemplateSummary]])
async def list_prompts(
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    _user: CurrentUserDependency,
) -> ApiResponse[list[PromptTemplateSummary]]:
    result = await AIManagementService(session, settings).list_prompts()
    return success_response(result, get_request_id(request))


@router.get(
    "/prompts/{template_id}/versions",
    response_model=ApiResponse[list[PromptVersionSummary]],
)
async def list_prompt_versions(
    template_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    _user: CurrentUserDependency,
) -> ApiResponse[list[PromptVersionSummary]]:
    result = await AIManagementService(session, settings).list_prompt_versions(template_id)
    return success_response(result, get_request_id(request))


@router.post(
    "/prompts/{template_id}/versions",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_prompt_version(
    template_id: UUID,
    payload: PromptVersionChangeRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await AIManagementService(session, settings).request_version_change(
        template_id, payload, user.id
    )
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation),
        get_request_id(request),
    )


@router.post(
    "/prompts/{template_id}/status",
    response_model=ApiResponse[ConfirmationTaskResponse],
)
async def request_prompt_status(
    template_id: UUID,
    payload: PromptStatusChangeRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ConfirmationTaskResponse]:
    confirmation = await AIManagementService(session, settings).request_status_change(
        template_id, payload, user.id
    )
    return success_response(
        ConfirmationTaskResponse.model_validate(confirmation),
        get_request_id(request),
    )


@router.get("/model-runtime", response_model=ApiResponse[ModelRuntimeSummary])
async def model_runtime(
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    _user: CurrentUserDependency,
) -> ApiResponse[ModelRuntimeSummary]:
    result = await AIManagementService(session, settings).model_runtime()
    return success_response(result, get_request_id(request))


@router.get("/model-invocations", response_model=ApiResponse[list[ModelInvocationSummary]])
async def model_invocations(
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    _user: CurrentUserDependency,
) -> ApiResponse[list[ModelInvocationSummary]]:
    result = await AIManagementService(session, settings).list_invocations()
    return success_response(result, get_request_id(request))


@router.get(
    "/evaluation/member3",
    response_model=ApiResponse[MemberThreeEvaluationSummary],
)
async def member_three_evaluation(
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    _user: CurrentUserDependency,
) -> ApiResponse[MemberThreeEvaluationSummary]:
    result = await AIManagementService(session, settings).evaluation()
    return success_response(result, get_request_id(request))
