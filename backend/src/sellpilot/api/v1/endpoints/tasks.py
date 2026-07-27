from uuid import UUID

from fastapi import APIRouter, Query, Request

from sellpilot.api.dependencies import CurrentUserDependency, SessionDependency
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, PageResult, success_response
from sellpilot.schemas.task import AgentTaskResponse
from sellpilot.services.task import TaskService

router = APIRouter()


@router.get("", response_model=ApiResponse[PageResult[AgentTaskResponse]])
async def list_tasks(
    request: Request,
    session: SessionDependency,
    current_user: CurrentUserDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ApiResponse[PageResult[AgentTaskResponse]]:
    tasks, total = await TaskService(session).list(page, page_size)
    result = PageResult[AgentTaskResponse](
        items=[AgentTaskResponse.model_validate(task) for task in tasks],
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
    task = await TaskService(session).get(task_id)
    return success_response(AgentTaskResponse.model_validate(task), get_request_id(request))
