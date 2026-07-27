from fastapi import APIRouter, Request

from sellpilot.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
)
from sellpilot.core.middleware import get_request_id
from sellpilot.core.response import ApiResponse, success_response
from sellpilot.schemas.auth import (
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
)
from sellpilot.services.auth import AuthService

router = APIRouter()


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    payload: LoginRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[TokenResponse]:
    _, token = await AuthService(session, settings).authenticate(payload.username, payload.password)
    return success_response(TokenResponse(access_token=token), get_request_id(request))


@router.get("/me", response_model=ApiResponse[CurrentUserResponse])
async def me(
    request: Request, current_user: CurrentUserDependency
) -> ApiResponse[CurrentUserResponse]:
    return success_response(
        CurrentUserResponse.model_validate(current_user), get_request_id(request)
    )


@router.post("/change-password", response_model=ApiResponse[CurrentUserResponse])
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> ApiResponse[CurrentUserResponse]:
    user = await AuthService(session, settings).change_password(
        current_user, payload.old_password, payload.new_password
    )
    return success_response(CurrentUserResponse.model_validate(user), get_request_id(request))
