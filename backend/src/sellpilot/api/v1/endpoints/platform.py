from fastapi import APIRouter, Request

from sellpilot.adapters.factory import create_platform_adapter
from sellpilot.api.dependencies import SettingsDependency
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.platform import PlatformStatusResponse

router = APIRouter()


@router.get("/status", response_model=ApiResponse[PlatformStatusResponse])
async def platform_status(
    request: Request, settings: SettingsDependency
) -> ApiResponse[PlatformStatusResponse]:
    adapter = create_platform_adapter(settings)
    ping = await adapter.ping()
    capabilities = await adapter.get_capabilities()
    return success_response(
        PlatformStatusResponse(**ping.model_dump(), capabilities=capabilities),
        get_request_id(request),
    )
