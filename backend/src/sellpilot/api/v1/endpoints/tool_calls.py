from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query, Request

from sellpilot.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
)
from sellpilot.core.enums import ToolCallStatus, ToolRiskLevel
from sellpilot.core.exceptions import ResourceNotFoundError
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, PageResult, success_response
from sellpilot.repositories.tool_call import ToolCallRepository
from sellpilot.schemas.tool import ToolCallResponse
from sellpilot.services.task import TaskService

router = APIRouter()


@router.get("", response_model=ApiResponse[PageResult[ToolCallResponse]])
async def list_tool_calls(
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tool_name: str | None = Query(default=None, min_length=1, max_length=100),
    status: ToolCallStatus | None = None,
    risk_level: ToolRiskLevel | None = None,
    task_id: UUID | None = None,
    task_step_id: UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> ApiResponse[PageResult[ToolCallResponse]]:
    if task_id is not None:
        await TaskService(session).get(task_id, user_id=current_user.id)
    items, total = await ToolCallRepository(session).list(
        page=page,
        page_size=page_size,
        tool_name=tool_name,
        status=status,
        risk_level=risk_level,
        task_id=task_id,
        task_step_id=task_step_id,
        user_id=current_user.id,
        created_from=created_from,
        created_to=created_to,
    )
    result = PageResult[ToolCallResponse](
        items=[
            ToolCallResponse.from_tool_call(
                item,
                max_bytes=settings.tool_audit_payload_max_bytes,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
    return success_response(result, get_request_id(request))


@router.get("/{tool_call_id}", response_model=ApiResponse[ToolCallResponse])
async def get_tool_call(
    tool_call_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[ToolCallResponse]:
    tool_call = await ToolCallRepository(session).get_owned(tool_call_id, current_user.id)
    if tool_call is None:
        raise ResourceNotFoundError("ToolCall not found")
    return success_response(
        ToolCallResponse.from_tool_call(
            tool_call,
            max_bytes=settings.tool_audit_payload_max_bytes,
        ),
        get_request_id(request),
    )
