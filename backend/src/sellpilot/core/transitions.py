from collections.abc import Mapping, Set

from sellpilot.core.enums import ConfirmationStatus, TaskStatus, TaskStepStatus
from sellpilot.core.exceptions import StateConflictError

TASK_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED}),
    TaskStatus.RUNNING: frozenset(
        {
            TaskStatus.WAITING_CONFIRMATION,
            TaskStatus.SUCCEEDED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.WAITING_CONFIRMATION: frozenset(
        {TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED}
    ),
    TaskStatus.SUCCEEDED: frozenset(),
    TaskStatus.FAILED: frozenset({TaskStatus.PENDING, TaskStatus.RUNNING}),
    TaskStatus.CANCELLED: frozenset(),
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

TASK_TERMINAL_STATUSES = frozenset({TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED})
CONFIRMATION_TERMINAL_STATUSES = frozenset(
    {
        ConfirmationStatus.SUCCEEDED,
        ConfirmationStatus.FAILED,
        ConfirmationStatus.CANCELED,
    }
)

TASK_STEP_TRANSITIONS: dict[TaskStepStatus, frozenset[TaskStepStatus]] = {
    TaskStepStatus.PENDING: frozenset(
        {TaskStepStatus.RUNNING, TaskStepStatus.SKIPPED, TaskStepStatus.CANCELLED}
    ),
    TaskStepStatus.RUNNING: frozenset(
        {
            TaskStepStatus.WAITING_CONFIRMATION,
            TaskStepStatus.SUCCEEDED,
            TaskStepStatus.FAILED,
            TaskStepStatus.CANCELLED,
        }
    ),
    TaskStepStatus.WAITING_CONFIRMATION: frozenset(
        {
            TaskStepStatus.RUNNING,
            TaskStepStatus.SUCCEEDED,
            TaskStepStatus.FAILED,
            TaskStepStatus.CANCELLED,
        }
    ),
    TaskStepStatus.SUCCEEDED: frozenset(),
    TaskStepStatus.FAILED: frozenset({TaskStepStatus.RUNNING}),
    TaskStepStatus.SKIPPED: frozenset(),
    TaskStepStatus.CANCELLED: frozenset(),
}


def _validate_transition[StatusT](
    current: StatusT,
    target: StatusT,
    transitions: Mapping[StatusT, Set[StatusT]],
    *,
    resource_name: str,
) -> None:
    if target not in transitions[current]:
        raise StateConflictError(f"{resource_name} cannot transition from {current} to {target}")


def validate_task_transition(
    current: TaskStatus,
    target: TaskStatus,
    *,
    allow_retry: bool = False,
) -> None:
    if current is TaskStatus.FAILED and not allow_retry:
        raise StateConflictError("Failed task retry requires explicit retry authorization")
    _validate_transition(
        current,
        target,
        TASK_TRANSITIONS,
        resource_name="Task",
    )


def validate_confirmation_transition(
    current: ConfirmationStatus,
    target: ConfirmationStatus,
) -> None:
    _validate_transition(
        current,
        target,
        CONFIRMATION_TRANSITIONS,
        resource_name="Confirmation",
    )


def validate_task_step_transition(
    current: TaskStepStatus,
    target: TaskStepStatus,
    *,
    allow_retry: bool = False,
) -> None:
    if current is TaskStepStatus.FAILED and not allow_retry:
        raise StateConflictError("Failed task step retry requires explicit retry authorization")
    _validate_transition(
        current,
        target,
        TASK_STEP_TRANSITIONS,
        resource_name="Task step",
    )
