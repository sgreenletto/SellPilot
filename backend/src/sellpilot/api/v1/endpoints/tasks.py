from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from sellpilot.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
)
from sellpilot.core.enums import OperationStatus, TaskStatus
from sellpilot.core.exceptions import ParameterError
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, PageResult, success_response
from sellpilot.repositories.operation_log import OperationLogRepository
from sellpilot.schemas.operation_log import OperationLogResponse
from sellpilot.schemas.task import (
    AgentTaskResponse,
    TaskCreateRequest,
    TaskExecutionResult,
    TaskStepResponse,
    WorkflowMetadata,
)
from sellpilot.services.task import TaskService
from sellpilot.services.task_center import TaskCenterService
from sellpilot.workflows.registry import WorkflowRegistry
from sellpilot.workflows.runner import TaskRunner

router = APIRouter()


def _workflow_registry(request: Request) -> WorkflowRegistry:
    return request.app.state.workflow_registry


def _runner(
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TaskRunner:
    return TaskRunner(
        _workflow_registry(request),
        request.app.state.tool_registry,
        session,
        settings,
    )


@router.get("/workflows", response_model=ApiResponse[list[WorkflowMetadata]])
async def list_workflows(
    request: Request,
    current_user: CurrentUserDependency,
) -> ApiResponse[list[WorkflowMetadata]]:
    return success_response(
        _workflow_registry(request).list_metadata(enabled_only=True),
        get_request_id(request),
    )


@router.post(
    "",
    response_model=ApiResponse[AgentTaskResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    payload: TaskCreateRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[AgentTaskResponse]:
    definition = _workflow_registry(request).get(payload.workflow_name)
    task = await TaskService(session, settings).create_persisted_workflow_task(
        definition,
        workflow_input=payload.workflow_input,
        created_by=current_user.id,
        request_id=get_request_id(request),
    )
    return success_response(AgentTaskResponse.from_task(task), get_request_id(request))


@router.get("", response_model=ApiResponse[PageResult[AgentTaskResponse]])
async def list_tasks(
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    workflow_name: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    task_type: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
) -> ApiResponse[PageResult[AgentTaskResponse]]:
    if created_from is not None and created_to is not None and created_from > created_to:
        raise ParameterError("created_from must not be later than created_to")
    tasks, total = await TaskService(session).list(
        page,
        page_size,
        user_id=current_user.id,
        status=task_status,
        workflow_name=workflow_name,
        task_type=task_type,
        created_from=created_from,
        created_to=created_to,
    )
    result = PageResult[AgentTaskResponse](
        items=[AgentTaskResponse.from_task(task) for task in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )
    return success_response(result, get_request_id(request))


@router.get("/{task_id}", response_model=ApiResponse[AgentTaskResponse])
async def get_task(
    task_id: UUID,
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[AgentTaskResponse]:
    task = await TaskService(session).get(task_id, user_id=current_user.id)
    actions = await TaskCenterService(
        session,
        _workflow_registry(request),
    ).available_actions(task)
    return success_response(
        AgentTaskResponse.from_task(task, available_actions=actions),
        get_request_id(request),
    )


@router.get(
    "/{task_id}/steps",
    response_model=ApiResponse[list[TaskStepResponse]],
)
async def list_task_steps(
    task_id: UUID,
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[list[TaskStepResponse]]:
    service = TaskService(session)
    await service.get(task_id, user_id=current_user.id)
    steps = await service.tasks.list_steps(task_id)
    return success_response(
        [TaskStepResponse.model_validate(step) for step in steps],
        get_request_id(request),
    )


@router.get(
    "/{task_id}/operation-logs",
    response_model=ApiResponse[PageResult[OperationLogResponse]],
)
async def list_task_operation_logs(
    task_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    event_type: str | None = Query(default=None, min_length=1, max_length=100),
    operation_status: Annotated[
        OperationStatus | None,
        Query(alias="status"),
    ] = None,
) -> ApiResponse[PageResult[OperationLogResponse]]:
    await TaskService(session).get(task_id, user_id=current_user.id)
    items, total = await OperationLogRepository(session).list_by_task(
        task_id,
        page=page,
        page_size=page_size,
        event_type=event_type,
        status=operation_status,
    )
    return success_response(
        PageResult[OperationLogResponse](
            items=[
                OperationLogResponse.from_operation_log(
                    item,
                    max_bytes=settings.tool_audit_payload_max_bytes,
                )
                for item in items
            ],
            total=total,
            page=page,
            page_size=page_size,
        ),
        get_request_id(request),
    )


async def _execute_response(
    result: TaskExecutionResult,
    request: Request,
) -> ApiResponse[TaskExecutionResult] | JSONResponse:
    payload = success_response(result, get_request_id(request))
    if result.confirmation_required:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=jsonable_encoder(payload),
        )
    return payload


@router.post(
    "/{task_id}/run",
    response_model=ApiResponse[TaskExecutionResult],
)
async def run_task(
    task_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[TaskExecutionResult] | JSONResponse:
    result = await _runner(request, session, settings).run(
        task_id,
        user_id=current_user.id,
        request_id=get_request_id(request),
    )
    return await _execute_response(result, request)


@router.post(
    "/{task_id}/resume",
    response_model=ApiResponse[TaskExecutionResult],
)
async def resume_task(
    task_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[TaskExecutionResult] | JSONResponse:
    result = await _runner(request, session, settings).resume(
        task_id,
        user_id=current_user.id,
        request_id=get_request_id(request),
    )
    return await _execute_response(result, request)


@router.post(
    "/{task_id}/retry",
    response_model=ApiResponse[TaskExecutionResult],
)
async def retry_task(
    task_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[TaskExecutionResult] | JSONResponse:
    result = await _runner(request, session, settings).retry(
        task_id,
        user_id=current_user.id,
        request_id=get_request_id(request),
    )
    return await _execute_response(result, request)


@router.post(
    "/{task_id}/rerun",
    response_model=ApiResponse[AgentTaskResponse],
    status_code=status.HTTP_201_CREATED,
)
async def rerun_task(
    task_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[AgentTaskResponse]:
    task = await _runner(request, session, settings).rerun(
        task_id,
        user_id=current_user.id,
        request_id=get_request_id(request),
    )
    return success_response(AgentTaskResponse.from_task(task), get_request_id(request))


@router.post(
    "/{task_id}/cancel",
    response_model=ApiResponse[AgentTaskResponse],
)
async def cancel_task(
    task_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[AgentTaskResponse]:
    task = await _runner(request, session, settings).cancel(
        task_id,
        user_id=current_user.id,
        request_id=get_request_id(request),
    )
    return success_response(AgentTaskResponse.from_task(task), get_request_id(request))
