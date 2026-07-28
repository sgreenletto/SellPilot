from fastapi import APIRouter, Request

from sellpilot.api.dependencies import CurrentUserDependency
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.assistant import (
    AssistantCapabilityResponse,
    AssistantPlanRequest,
    AssistantPlanResponse,
)
from sellpilot.services.assistant import (
    AssistantCapabilityRegistry,
    AssistantPlanService,
)

router = APIRouter()


def _registry(request: Request) -> AssistantCapabilityRegistry:
    return request.app.state.assistant_capability_registry


@router.get(
    "/capabilities",
    response_model=ApiResponse[list[AssistantCapabilityResponse]],
)
async def list_assistant_capabilities(
    request: Request,
    _current_user: CurrentUserDependency,
) -> ApiResponse[list[AssistantCapabilityResponse]]:
    return success_response(
        _registry(request).list_public(),
        get_request_id(request),
    )


@router.post(
    "/plan",
    response_model=ApiResponse[AssistantPlanResponse],
)
async def plan_assistant_message(
    payload: AssistantPlanRequest,
    request: Request,
    _current_user: CurrentUserDependency,
) -> ApiResponse[AssistantPlanResponse]:
    plan = AssistantPlanService(_registry(request)).plan(payload.message)
    return success_response(plan, get_request_id(request))
