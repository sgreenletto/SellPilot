from typing import Any

from sellpilot.core.exceptions import DuplicateOperationError, ResourceNotFoundError


class AgentRegistry:
    """Registry for future agent factories; no business agents are registered yet."""

    def __init__(self) -> None:
        self._agents: dict[str, Any] = {}

    def register(self, name: str, agent: Any) -> None:
        if name in self._agents:
            raise DuplicateOperationError(f"Agent '{name}' is already registered")
        self._agents[name] = agent

    def get(self, name: str) -> Any:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise ResourceNotFoundError(f"Agent '{name}' is not registered") from exc

    def list(self) -> list[str]:
        return sorted(self._agents)
