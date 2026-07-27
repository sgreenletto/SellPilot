from typing import Any


class AppException(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "APP_ERROR",
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
        super().__init__(message, code="PARAMETER_ERROR", status_code=422, details=details)


class UnauthenticatedError(AppException):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, code="UNAUTHENTICATED", status_code=401)


class ResourceNotFoundError(AppException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="RESOURCE_NOT_FOUND", status_code=404)


class StateConflictError(AppException):
    def __init__(self, message: str = "Resource state conflict") -> None:
        super().__init__(message, code="STATE_CONFLICT", status_code=409)


class DuplicateOperationError(AppException):
    def __init__(self, message: str = "Duplicate operation") -> None:
        super().__init__(message, code="DUPLICATE_OPERATION", status_code=409)


class PlatformNotConfiguredError(AppException):
    def __init__(self, message: str = "Platform adapter is not configured") -> None:
        super().__init__(message, code="PLATFORM_NOT_CONFIGURED", status_code=503)


class PlatformFeatureNotImplementedError(AppException):
    def __init__(self, message: str = "Platform feature is not implemented") -> None:
        super().__init__(message, code="PLATFORM_FEATURE_NOT_IMPLEMENTED", status_code=501)


class ToolFailureError(AppException):
    def __init__(self, message: str = "Tool execution failed") -> None:
        super().__init__(message, code="TOOL_FAILED", status_code=500)


class ToolConfirmationRequiredError(AppException):
    def __init__(self, message: str = "Tool execution requires confirmation") -> None:
        super().__init__(message, code="TOOL_CONFIRMATION_REQUIRED", status_code=409)


class WorkflowFailureError(AppException):
    def __init__(self, message: str = "Workflow execution failed") -> None:
        super().__init__(message, code="WORKFLOW_FAILED", status_code=500)


class DatabaseUnavailableError(AppException):
    def __init__(self, message: str = "Database is unavailable") -> None:
        super().__init__(message, code="DATABASE_UNAVAILABLE", status_code=503)


class ConfirmationExecutorNotFoundError(AppException):
    def __init__(self, operation_type: str) -> None:
        super().__init__(
            f"No confirmation executor is registered for operation type '{operation_type}'",
            code="CONFIRMATION_EXECUTOR_NOT_FOUND",
            status_code=409,
        )
