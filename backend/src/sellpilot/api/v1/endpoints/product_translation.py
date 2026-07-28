from uuid import UUID

from fastapi import APIRouter, Request

from sellpilot.api.dependencies import CurrentUserDependency, SessionDependency, SettingsDependency
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.product_translation import (
    ProductTranslationProviderStatus,
    ProductTranslationRequest,
    ProductTranslationTask,
)
from sellpilot.services.product_translation import ProductTranslationService

router = APIRouter()


@router.get("/status", response_model=ApiResponse[ProductTranslationProviderStatus])
async def status(
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    _user: CurrentUserDependency,
) -> ApiResponse[ProductTranslationProviderStatus]:
    data = ProductTranslationService(session, settings).provider_status()
    return success_response(data, get_request_id(request))


@router.post("/requests", response_model=ApiResponse[ProductTranslationTask])
async def request_translation(
    payload: ProductTranslationRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ProductTranslationTask]:
    data = await ProductTranslationService(session, settings).request(payload, user.id)
    return success_response(data, get_request_id(request))


@router.get("/tasks/{task_id}", response_model=ApiResponse[ProductTranslationTask])
async def get_task(
    task_id: UUID,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    user: CurrentUserDependency,
) -> ApiResponse[ProductTranslationTask]:
    data = await ProductTranslationService(session, settings).get(task_id, user.id)
    return success_response(data, get_request_id(request))
