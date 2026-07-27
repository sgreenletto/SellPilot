import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sellpilot.api.router import build_api_router
from sellpilot.core.config import Settings, get_settings
from sellpilot.core.exceptions import AppException
from sellpilot.core.logging import configure_logging
from sellpilot.core.middleware import RequestIdMiddleware, get_request_id
from sellpilot.core.response import ApiResponse

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    current_settings = settings or get_settings()
    configure_logging(current_settings)

    application = FastAPI(
        title=current_settings.app_name,
        version=current_settings.app_version,
        debug=current_settings.debug,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=current_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestIdMiddleware)
    application.include_router(build_api_router(current_settings))

    @application.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        payload = ApiResponse[object](
            code=exc.code,
            message=exc.message,
            data=exc.details,
            request_id=get_request_id(request),
        )
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(payload))

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        payload = ApiResponse[object](
            code="PARAMETER_ERROR",
            message="Invalid request parameters",
            data=jsonable_encoder(exc.errors()),
            request_id=get_request_id(request),
        )
        return JSONResponse(status_code=422, content=jsonable_encoder(payload))

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled request error request_id=%s exception_type=%s",
            get_request_id(request),
            type(exc).__name__,
        )
        payload = ApiResponse[object](
            code="INTERNAL_ERROR",
            message="Internal server error",
            data=None,
            request_id=get_request_id(request),
        )
        return JSONResponse(status_code=500, content=jsonable_encoder(payload))

    return application


app = create_app()
