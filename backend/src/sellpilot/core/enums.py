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
