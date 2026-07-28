from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from sellpilot.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
)
from sellpilot.core.enums import ToolCallerType, ToolCallStatus
from sellpilot.core.exceptions import ErrorCode
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.tool import ToolExecuteRequest
from sellpilot.tools.contracts import (
    ToolExecutionContext,
    ToolExecutionResult,
    ToolPublicMetadata,
)
from sellpilot.tools.executor import ToolExecutor
from sellpilot.tools.registry import ToolRegistry

router = APIRouter()


def get_request_registry(request: Request) -> ToolRegistry:
    return request.app.state.tool_registry


@router.get("", response_model=ApiResponse[list[ToolPublicMetadata]])
async def list_tools(
    request: Request,
    current_user: CurrentUserDependency,
) -> ApiResponse[list[ToolPublicMetadata]]:
    return success_response(
        get_request_registry(request).list_metadata(),
        get_request_id(request),
    )


@router.get("/{tool_name}", response_model=ApiResponse[ToolPublicMetadata])
async def get_tool(
    tool_name: str,
    request: Request,
    current_user: CurrentUserDependency,
) -> ApiResponse[ToolPublicMetadata]:
    return success_response(
        get_request_registry(request).metadata(tool_name),
        get_request_id(request),
    )


@router.post(
    "/{tool_name}/execute",
    response_model=ApiResponse[ToolExecutionResult],
)
async def execute_tool(
    tool_name: str,
    payload: ToolExecuteRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[ToolExecutionResult] | JSONResponse:
    request_id = get_request_id(request)
    result = await ToolExecutor(
        get_request_registry(request),
        session,
        settings,
    ).execute(
        tool_name,
        payload.input,
        ToolExecutionContext(
            request_id=request_id,
            user_id=current_user.id,
            task_id=payload.task_id,
            task_step_id=payload.task_step_id,
            idempotency_key=payload.idempotency_key,
            caller_type=ToolCallerType.API,
            caller_name="internal_tool_api",
        ),
        target_type=payload.target_type,
        target_id=payload.target_id,
        before_snapshot=payload.before_snapshot,
        after_snapshot=payload.after_snapshot,
        risk_warning=payload.risk_warning,
    )
    if result.status is ToolCallStatus.SUCCEEDED:
        return success_response(result, request_id)
    if result.confirmation_required:
        response = success_response(result, request_id)
        return JSONResponse(status_code=202, content=jsonable_encoder(response))
    status_code = {
        ErrorCode.PARAMETER_ERROR: 422,
        ErrorCode.TOOL_INPUT_INVALID: 422,
        ErrorCode.TOOL_OUTPUT_INVALID: 502,
        ErrorCode.TOOL_TIMEOUT: 504,
        ErrorCode.TOOL_RETRY_EXHAUSTED: 503,
        ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE: 503,
        ErrorCode.MOCK_PLATFORM_FAILED: 502,
        ErrorCode.TOOL_CONFIRMATION_INVALID: 409,
        ErrorCode.TOOL_IDEMPOTENCY_CONFLICT: 409,
    }.get(result.error_code or "", 500)
    response = ApiResponse[ToolExecutionResult](
        code=result.error_code or "TOOL_EXECUTION_FAILED",
        message=result.error_message or "Tool execution failed",
        data=result,
        request_id=request_id,
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(response))
