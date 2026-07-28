from __future__ import annotations

from sellpilot.core.config import Settings
from sellpilot.core.enums import ToolRiskLevel
from sellpilot.core.exceptions import (
    ParameterError,
    ToolAlreadyRegisteredError,
    ToolDisabledError,
    ToolNotExposedError,
    ToolNotFoundError,
    ToolVersionConflictError,
)
from sellpilot.tools.contracts import ToolDefinition, ToolPublicMetadata
from sellpilot.tools.sanitization import redact_nested


def _version_tuple(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


class ToolRegistry:
    """Validated tool definition catalog. Execution belongs to ToolExecutor."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ToolAlreadyRegisteredError(definition.name)
        timeout = definition.timeout_seconds or self._settings.tool_default_timeout_seconds
        if timeout > self._settings.tool_max_timeout_seconds:
            raise ParameterError(
                f"Tool timeout must not exceed {self._settings.tool_max_timeout_seconds:g} seconds"
            )
        if (
            definition.risk_level is ToolRiskLevel.READ
            and definition.retry_policy.max_attempts > self._settings.tool_read_max_attempts
        ):
            raise ParameterError("Read tool attempts exceed the configured TOOL_READ_MAX_ATTEMPTS")
        self._tools[definition.name] = definition.model_copy(update={"timeout_seconds": timeout})

    def contains(self, name: str) -> bool:
        return name in self._tools

    def get(
        self,
        name: str,
        *,
        required_version: str | None = None,
        require_enabled: bool = True,
    ) -> ToolDefinition:
        try:
            definition = self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(name) from exc
        if require_enabled and not definition.enabled:
            raise ToolDisabledError(name)
        if required_version is not None and definition.version != required_version:
            raise ToolVersionConflictError(name, required_version, definition.version)
        return definition

    def is_version_compatible(self, name: str, required_version: str) -> bool:
        definition = self.get(name, require_enabled=False)
        registered = _version_tuple(definition.version)
        required = _version_tuple(required_version)
        return registered[0] == required[0] and registered >= required

    def list(self, *, enabled_only: bool = False) -> list[ToolDefinition]:
        return [
            self._tools[name]
            for name in sorted(self._tools)
            if not enabled_only or self._tools[name].enabled
        ]

    def list_mcp(self) -> list[ToolDefinition]:
        return [
            definition
            for definition in self.list(enabled_only=True)
            if definition.expose_to_mcp
            and (
                definition.risk_level is not ToolRiskLevel.HIGH_RISK
                or definition.allow_high_risk_mcp
            )
        ]

    def get_mcp(self, name: str) -> ToolDefinition:
        definition = self.get(name)
        if definition not in self.list_mcp():
            raise ToolNotExposedError(name)
        return definition

    def metadata(
        self,
        name: str,
        *,
        require_enabled: bool = False,
    ) -> ToolPublicMetadata:
        return self._metadata(self.get(name, require_enabled=require_enabled))

    def list_metadata(self, *, enabled_only: bool = False) -> list[ToolPublicMetadata]:
        return [self._metadata(definition) for definition in self.list(enabled_only=enabled_only)]

    @staticmethod
    def _metadata(definition: ToolDefinition) -> ToolPublicMetadata:
        input_schema = redact_nested(
            definition.input_schema.model_json_schema(),
            extra_sensitive_fields=definition.sensitive_input_fields,
        )
        output_schema = redact_nested(
            definition.output_schema.model_json_schema(),
            extra_sensitive_fields=definition.sensitive_output_fields,
        )
        return ToolPublicMetadata(
            name=definition.name,
            version=definition.version,
            description=definition.description,
            risk_level=definition.risk_level,
            timeout_seconds=definition.timeout_seconds or 0,
            enabled=definition.enabled,
            expose_to_mcp=definition.expose_to_mcp,
            confirmation_required=definition.confirmation_required,
            input_json_schema=input_schema if isinstance(input_schema, dict) else {},
            output_json_schema=output_schema if isinstance(output_schema, dict) else {},
        )
