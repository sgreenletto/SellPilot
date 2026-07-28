from __future__ import annotations

from sellpilot.core.config import Settings
from sellpilot.core.exceptions import (
    ParameterError,
    WorkflowAlreadyRegisteredError,
    WorkflowDisabledError,
    WorkflowNotFoundError,
    WorkflowVersionConflictError,
)
from sellpilot.workflows.contracts import WorkflowDefinition, WorkflowMetadata


class WorkflowRegistry:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register(self, definition: WorkflowDefinition) -> None:
        if definition.name in self._workflows:
            raise WorkflowAlreadyRegisteredError(definition.name)
        if self._settings is not None:
            if definition.max_steps > self._settings.task_max_steps:
                raise ParameterError("Workflow max_steps exceeds TASK_MAX_STEPS")
            if definition.max_task_attempts > self._settings.task_max_attempts:
                raise ParameterError("Workflow attempts exceed TASK_MAX_ATTEMPTS")
            for node in definition.nodes:
                timeout = node.timeout_seconds or self._settings.task_default_node_timeout_seconds
                if timeout > self._settings.task_max_node_timeout_seconds:
                    raise ParameterError(
                        "Workflow node timeout exceeds TASK_MAX_NODE_TIMEOUT_SECONDS"
                    )
        self._workflows[definition.name] = definition

    def contains(self, name: str) -> bool:
        return name in self._workflows

    def get(
        self,
        name: str,
        *,
        required_version: str | None = None,
        require_enabled: bool = True,
    ) -> WorkflowDefinition:
        try:
            definition = self._workflows[name]
        except KeyError as exc:
            raise WorkflowNotFoundError(name) from exc
        if require_enabled and not definition.enabled:
            raise WorkflowDisabledError(name)
        if required_version is not None and definition.version != required_version:
            raise WorkflowVersionConflictError(name, required_version, definition.version)
        return definition

    def list(self, *, enabled_only: bool = False) -> list[WorkflowDefinition]:
        return [
            self._workflows[name]
            for name in sorted(self._workflows)
            if not enabled_only or self._workflows[name].enabled
        ]

    def list_metadata(self, *, enabled_only: bool = False) -> list[WorkflowMetadata]:
        return [
            WorkflowMetadata(
                name=definition.name,
                version=definition.version,
                description=definition.description,
                task_type=definition.task_type,
                enabled=definition.enabled,
                resumable=definition.resumable,
                max_steps=definition.max_steps,
                max_task_attempts=definition.max_task_attempts,
            )
            for definition in self.list(enabled_only=enabled_only)
        ]
