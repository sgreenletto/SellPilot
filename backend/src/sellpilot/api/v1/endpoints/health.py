from fastapi import APIRouter, Request
from sqlalchemy import text

from sellpilot.api.dependencies import SessionDependency
from sellpilot.core.exceptions import DatabaseUnavailableError
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response

router = APIRouter()


@router.get("/live", response_model=ApiResponse[dict[str, str]])
async def live(request: Request) -> ApiResponse[dict[str, str]]:
    return success_response({"status": "ok"}, get_request_id(request))


@router.get("/ready", response_model=ApiResponse[dict[str, str]])
async def ready(request: Request, session: SessionDependency) -> ApiResponse[dict[str, str]]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise DatabaseUnavailableError() from exc
    return success_response({"status": "ready", "database": "reachable"}, get_request_id(request))
