from typing import Any

from sellpilot.core.exceptions import DuplicateOperationError, ResourceNotFoundError


class WorkflowRegistry:
    def __init__(self) -> None:
        self._workflows: dict[str, Any] = {}

    def register(self, name: str, workflow: Any) -> None:
        if name in self._workflows:
            raise DuplicateOperationError(f"Workflow '{name}' is already registered")
        self._workflows[name] = workflow

    def get(self, name: str) -> Any:
        try:
            return self._workflows[name]
        except KeyError as exc:
            raise ResourceNotFoundError(f"Workflow '{name}' is not registered") from exc

    def list(self) -> list[str]:
        return sorted(self._workflows)
