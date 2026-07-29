import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sellpilot.api.router import build_api_router
from sellpilot.core.config import Settings, get_settings
from sellpilot.core.exceptions import AppException, ErrorCode
from sellpilot.core.logging import configure_logging
from sellpilot.core.middleware import RequestIdMiddleware, get_request_id
from sellpilot.core.response import ApiResponse, ValidationIssue
from sellpilot.tools.runtime import build_tool_registry
from sellpilot.workflows.runtime import build_workflow_registry

logger = logging.getLogger(__name__)

DEFAULT_ADMIN = "admin"
DEFAULT_ADMIN_PW = "admin123admin"


async def _auto_init_admin(settings: Settings) -> None:
    """若 users 表为空则自动创建默认管理员。"""
    from sellpilot.db.session import get_session_factory
    from sellpilot.repositories.user import UserRepository
    from sellpilot.services.auth import AuthService

    try:
        async with get_session_factory()() as session:
            repo = UserRepository(session)
            current = await repo.get_by_username(DEFAULT_ADMIN)
            if current is not None:
                logger.info("Admin user already exists")
                return
            await AuthService(session, settings).create_admin(DEFAULT_ADMIN, DEFAULT_ADMIN_PW)
            await session.commit()
            logger.info("Auto-created admin user: %s", DEFAULT_ADMIN)
    except Exception as exc:
        logger.warning("Auto-init skipped (DB may need migrations): %s", exc)


def create_app(settings: Settings | None = None) -> FastAPI:
    current_settings = settings or get_settings()
    configure_logging(current_settings)

    application = FastAPI(
        title=current_settings.app_name,
        version=current_settings.app_version,
        debug=current_settings.debug,
    )

    @application.on_event("startup")
    async def _startup() -> None:
        await _auto_init_admin(current_settings)

    application.state.tool_registry = build_tool_registry(current_settings)
    application.state.workflow_registry = build_workflow_registry(current_settings)
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
    async def _app_exc(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(ApiResponse[object](
                code=exc.code, message=exc.message,
                data=exc.details, request_id=get_request_id(request),
            )),
        )

    @application.exception_handler(RequestValidationError)
    async def _validation_exc(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(ApiResponse[object](
                code=ErrorCode.PARAMETER_ERROR, message="Invalid request parameters",
                data=[ValidationIssue(
                    field=".".join(str(p) for p in e["loc"]),
                    message=e["msg"], type=e["type"],
                ) for e in exc.errors()],
                request_id=get_request_id(request),
            )),
        )

    @application.exception_handler(Exception)
    async def _unexpected_exc(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled error request_id=%s type=%s",
            get_request_id(request), type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(ApiResponse[object](
                code=ErrorCode.INTERNAL_ERROR, message="Internal server error",
                data=None, request_id=get_request_id(request),
            )),
        )

    return application


app = create_app()
