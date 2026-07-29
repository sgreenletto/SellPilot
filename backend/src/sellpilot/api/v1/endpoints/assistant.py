from fastapi import APIRouter, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from sellpilot.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
)
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.assistant import (
    AssistantCapabilityResponse,
    AssistantPlanRequest,
    AssistantPlanResponse,
    AssistantTaskRequest,
    AssistantTaskResponse,
)
from sellpilot.schemas.task import AgentTaskResponse
from sellpilot.services.assistant import (
    AssistantCapabilityRegistry,
    AssistantPlanService,
)
from sellpilot.services.assistant_task import AssistantTaskService

router = APIRouter()


def _registry(request: Request) -> AssistantCapabilityRegistry:
    return request.app.state.assistant_capability_registry


def _task_service(
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
) -> AssistantTaskService:
    return AssistantTaskService(
        capabilities=_registry(request),
        workflows=request.app.state.workflow_registry,
        tools=request.app.state.tool_registry,
        session=session,
        settings=settings,
    )


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


@router.post(
    "/tasks",
    response_model=ApiResponse[AssistantTaskResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_assistant_task(
    payload: AssistantTaskRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[AssistantTaskResponse] | JSONResponse:
    request_id = get_request_id(request)
    result = await _task_service(request, session, settings).create(
        message=payload.message,
        execution_mode=payload.execution_mode,
        user_id=current_user.id,
        request_id=request_id,
    )
    response = success_response(result, request_id)
    if result.confirmation_required and result.task_status.value == "waiting_confirmation":
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=jsonable_encoder(response),
        )
    return response


@router.get(
    "/tasks",
    response_model=ApiResponse[list[AgentTaskResponse]],
)
async def list_recent_assistant_tasks(
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
    limit: int = Query(default=5, ge=1, le=20),
) -> ApiResponse[list[AgentTaskResponse]]:
    tasks = await _task_service(request, session, settings).list_recent(
        user_id=current_user.id,
        limit=limit,
    )
    return success_response(
        [AgentTaskResponse.from_task(task) for task in tasks],
        get_request_id(request),
    )
