from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    APP_ERROR = "APP_ERROR"
    PARAMETER_ERROR = "PARAMETER_ERROR"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    STATE_CONFLICT = "STATE_CONFLICT"
    DUPLICATE_OPERATION = "DUPLICATE_OPERATION"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    DATA_IMPORT_FAILED = "DATA_IMPORT_FAILED"
    MODEL_CALL_FAILED = "MODEL_CALL_FAILED"
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_DISABLED = "TOOL_DISABLED"
    TOOL_ALREADY_REGISTERED = "TOOL_ALREADY_REGISTERED"
    TOOL_INPUT_INVALID = "TOOL_INPUT_INVALID"
    TOOL_OUTPUT_INVALID = "TOOL_OUTPUT_INVALID"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    TOOL_CONFIRMATION_REQUIRED = "TOOL_CONFIRMATION_REQUIRED"
    TOOL_CONFIRMATION_INVALID = "TOOL_CONFIRMATION_INVALID"
    TOOL_IDEMPOTENCY_CONFLICT = "TOOL_IDEMPOTENCY_CONFLICT"
    TOOL_VERSION_CONFLICT = "TOOL_VERSION_CONFLICT"
    TOOL_NOT_EXPOSED = "TOOL_NOT_EXPOSED"
    TOOL_RETRY_EXHAUSTED = "TOOL_RETRY_EXHAUSTED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    MOCK_PLATFORM_FAILED = "MOCK_PLATFORM_FAILED"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"
    PLATFORM_NOT_CONFIGURED = "PLATFORM_NOT_CONFIGURED"
    PLATFORM_FEATURE_NOT_IMPLEMENTED = "PLATFORM_FEATURE_NOT_IMPLEMENTED"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    CONFIRMATION_EXECUTOR_NOT_FOUND = "CONFIRMATION_EXECUTOR_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode | str = ErrorCode.APP_ERROR,
        status_code: int = 400,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class ParameterError(AppException):
    def __init__(self, message: str = "Invalid request parameters", details: Any = None) -> None:
        super().__init__(
            message,
            code=ErrorCode.PARAMETER_ERROR,
            status_code=422,
            details=details,
        )


class UnauthenticatedError(AppException):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, code=ErrorCode.UNAUTHENTICATED, status_code=401)


class PermissionDeniedError(AppException):
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message, code=ErrorCode.PERMISSION_DENIED, status_code=403)


class ResourceNotFoundError(AppException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code=ErrorCode.RESOURCE_NOT_FOUND, status_code=404)


class StateConflictError(AppException):
    def __init__(self, message: str = "Resource state conflict") -> None:
        super().__init__(message, code=ErrorCode.STATE_CONFLICT, status_code=409)


class DuplicateOperationError(AppException):
    def __init__(self, message: str = "Duplicate operation") -> None:
        super().__init__(message, code=ErrorCode.DUPLICATE_OPERATION, status_code=409)


class IdempotencyConflictError(AppException):
    def __init__(self, message: str = "Idempotency key conflicts with another request") -> None:
        super().__init__(message, code=ErrorCode.IDEMPOTENCY_CONFLICT, status_code=409)


class DataImportFailureError(AppException):
    def __init__(self, message: str = "Data import failed") -> None:
        super().__init__(message, code=ErrorCode.DATA_IMPORT_FAILED, status_code=422)


class ModelCallFailureError(AppException):
    def __init__(self, message: str = "Model call failed") -> None:
        super().__init__(message, code=ErrorCode.MODEL_CALL_FAILED, status_code=502)


class PlatformNotConfiguredError(AppException):
    def __init__(self, message: str = "Platform adapter is not configured") -> None:
        super().__init__(message, code=ErrorCode.PLATFORM_NOT_CONFIGURED, status_code=503)


class PlatformFeatureNotImplementedError(AppException):
    def __init__(self, message: str = "Platform feature is not implemented") -> None:
        super().__init__(
            message,
            code=ErrorCode.PLATFORM_FEATURE_NOT_IMPLEMENTED,
            status_code=501,
        )


class MockPlatformFailureError(AppException):
    def __init__(self, message: str = "Mock platform operation failed") -> None:
        super().__init__(message, code=ErrorCode.MOCK_PLATFORM_FAILED, status_code=502)


class ExternalServiceUnavailableError(AppException):
    def __init__(self, message: str = "External service is unavailable") -> None:
        super().__init__(
            message,
            code=ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE,
            status_code=503,
        )


class ToolFailureError(AppException):
    def __init__(self, message: str = "Tool execution failed") -> None:
        super().__init__(message, code=ErrorCode.TOOL_FAILED, status_code=500)


class ToolNotFoundError(AppException):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Tool '{name}' is not registered",
            code=ErrorCode.TOOL_NOT_FOUND,
            status_code=404,
        )


class ToolDisabledError(AppException):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Tool '{name}' is disabled",
            code=ErrorCode.TOOL_DISABLED,
            status_code=409,
        )


class ToolAlreadyRegisteredError(AppException):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Tool '{name}' is already registered",
            code=ErrorCode.TOOL_ALREADY_REGISTERED,
            status_code=409,
        )


class ToolVersionConflictError(AppException):
    def __init__(self, name: str, required: str, registered: str) -> None:
        super().__init__(
            f"Tool '{name}' version {required} is not compatible with registered version "
            f"{registered}",
            code=ErrorCode.TOOL_VERSION_CONFLICT,
            status_code=409,
        )


class ToolNotExposedError(AppException):
    def __init__(self, name: str) -> None:
        super().__init__(
            f"Tool '{name}' is not exposed to MCP",
            code=ErrorCode.TOOL_NOT_EXPOSED,
            status_code=403,
        )


class ToolConfirmationInvalidError(AppException):
    def __init__(self, message: str = "Tool confirmation is invalid") -> None:
        super().__init__(
            message,
            code=ErrorCode.TOOL_CONFIRMATION_INVALID,
            status_code=409,
        )


class ToolIdempotencyConflictError(AppException):
    def __init__(self, message: str = "Tool idempotency key conflicts with another invocation"):
        super().__init__(
            message,
            code=ErrorCode.TOOL_IDEMPOTENCY_CONFLICT,
            status_code=409,
        )


class ToolConfirmationRequiredError(AppException):
    def __init__(self, message: str = "Tool execution requires confirmation") -> None:
        super().__init__(
            message,
            code=ErrorCode.TOOL_CONFIRMATION_REQUIRED,
            status_code=409,
        )


class WorkflowFailureError(AppException):
    def __init__(self, message: str = "Workflow execution failed") -> None:
        super().__init__(message, code=ErrorCode.WORKFLOW_FAILED, status_code=500)


class DatabaseUnavailableError(AppException):
    def __init__(self, message: str = "Database is unavailable") -> None:
        super().__init__(message, code=ErrorCode.DATABASE_UNAVAILABLE, status_code=503)


class ConfirmationExecutorNotFoundError(AppException):
    def __init__(self, operation_type: str) -> None:
        super().__init__(
            f"No confirmation executor is registered for operation type '{operation_type}'",
            code=ErrorCode.CONFIRMATION_EXECUTOR_NOT_FOUND,
            status_code=409,
        )
