from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class TaskStepStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ToolCallStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    TIMED_OUT = "TIMED_OUT"


class ConfirmationStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class OperationStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class RiskLevel(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    HIGH_RISK = "HIGH_RISK"


class AnalysisStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class ImprovementReportStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    ARCHIVED = "ARCHIVED"


class ImprovementSuggestionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    IGNORED = "IGNORED"
    ARCHIVED = "ARCHIVED"


class ProductContentStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class PromptStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class ModelInvocationStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class GeneratedReportStatus(StrEnum):
    READY = "READY"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


TASK_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.RUNNING, TaskStatus.FAILED}),
    TaskStatus.RUNNING: frozenset({TaskStatus.SUCCEEDED, TaskStatus.FAILED}),
    TaskStatus.SUCCEEDED: frozenset(),
    TaskStatus.FAILED: frozenset(),
}

CONFIRMATION_TRANSITIONS: dict[ConfirmationStatus, frozenset[ConfirmationStatus]] = {
    ConfirmationStatus.PENDING: frozenset(
        {ConfirmationStatus.CONFIRMED, ConfirmationStatus.CANCELED}
    ),
    ConfirmationStatus.CONFIRMED: frozenset(
        {ConfirmationStatus.EXECUTING, ConfirmationStatus.FAILED}
    ),
    ConfirmationStatus.EXECUTING: frozenset(
        {ConfirmationStatus.SUCCEEDED, ConfirmationStatus.FAILED}
    ),
    ConfirmationStatus.SUCCEEDED: frozenset(),
    ConfirmationStatus.FAILED: frozenset(),
    ConfirmationStatus.CANCELED: frozenset(),
}
