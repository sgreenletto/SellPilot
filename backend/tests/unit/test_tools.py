import pytest
from pydantic import BaseModel, ValidationError

from sellpilot.core.enums import ToolRiskLevel
from sellpilot.core.exceptions import (
    ParameterError,
    ToolAlreadyRegisteredError,
    ToolDisabledError,
    ToolNotExposedError,
    ToolNotFoundError,
    ToolVersionConflictError,
)
from sellpilot.tools.contracts import (
    RetryPolicy,
    ToolDefinition,
    ToolExecutionContext,
)
from sellpilot.tools.registry import ToolRegistry


class NumberInput(BaseModel):
    value: int
    password: str | None = None


class NumberOutput(BaseModel):
    doubled: int


async def double_handler(payload: BaseModel, context: ToolExecutionContext) -> NumberOutput:
    validated = NumberInput.model_validate(payload)
    return NumberOutput(doubled=validated.value * 2)


def definition(
    *,
    name: str = "double",
    version: str = "1.0.0",
    risk_level: ToolRiskLevel = ToolRiskLevel.READ,
    timeout: float | None = 1,
    enabled: bool = True,
    expose_to_mcp: bool = False,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        version=version,
        description="Double a number for runtime tests",
        input_schema=NumberInput,
        output_schema=NumberOutput,
        risk_level=risk_level,
        timeout_seconds=timeout,
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_delay_ms=0,
            max_delay_ms=0,
            backoff_multiplier=1,
        ),
        idempotent=True,
        expose_to_mcp=expose_to_mcp,
        enabled=enabled,
        sensitive_input_fields=frozenset({"password"}),
        handler=double_handler,
    )


def test_tool_registry_register_get_contains_and_stable_order(test_settings):
    registry = ToolRegistry(test_settings)
    registry.register(definition(name="z_tool"))
    registry.register(definition(name="a_tool"))

    assert registry.contains("a_tool") is True
    assert registry.get("a_tool").version == "1.0.0"
    assert [item.name for item in registry.list()] == ["a_tool", "z_tool"]


def test_tool_registry_rejects_duplicate_names(test_settings):
    registry = ToolRegistry(test_settings)
    registry.register(definition())
    with pytest.raises(ToolAlreadyRegisteredError) as error:
        registry.register(definition())
    assert error.value.code == "TOOL_ALREADY_REGISTERED"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "Invalid-Name"),
        ("version", "v1"),
    ],
)
def test_tool_definition_rejects_invalid_identity(field, value):
    values = {field: value}
    with pytest.raises(ValidationError):
        definition(**values)


def test_tool_definition_rejects_missing_schema():
    with pytest.raises(ValidationError):
        ToolDefinition(
            name="missing_schema",
            version="1.0.0",
            description="Invalid test definition",
            input_schema=None,
            output_schema=NumberOutput,
            risk_level=ToolRiskLevel.READ,
            retry_policy=RetryPolicy(
                max_attempts=1,
                initial_delay_ms=0,
                max_delay_ms=0,
                backoff_multiplier=1,
            ),
            idempotent=True,
            expose_to_mcp=False,
            handler=double_handler,
        )


def test_registry_rejects_timeout_over_configured_limit(test_settings):
    registry = ToolRegistry(test_settings)
    with pytest.raises(ParameterError, match="must not exceed"):
        registry.register(definition(timeout=test_settings.tool_max_timeout_seconds + 1))


def test_registry_filters_disabled_and_mcp_tools(test_settings):
    registry = ToolRegistry(test_settings)
    registry.register(definition(name="public_tool", expose_to_mcp=True))
    registry.register(definition(name="internal_tool"))
    registry.register(definition(name="disabled_tool", enabled=False, expose_to_mcp=True))

    assert [item.name for item in registry.list(enabled_only=True)] == [
        "internal_tool",
        "public_tool",
    ]
    assert [item.name for item in registry.list_mcp()] == ["public_tool"]
    with pytest.raises(ToolDisabledError):
        registry.get("disabled_tool")
    with pytest.raises(ToolNotExposedError):
        registry.get_mcp("internal_tool")


def test_registry_not_found_and_version_conflict_are_structured(test_settings):
    registry = ToolRegistry(test_settings)
    registry.register(definition())
    with pytest.raises(ToolNotFoundError) as missing:
        registry.get("missing")
    assert missing.value.code == "TOOL_NOT_FOUND"
    with pytest.raises(ToolVersionConflictError) as conflict:
        registry.get("double", required_version="2.0.0")
    assert conflict.value.code == "TOOL_VERSION_CONFLICT"
    assert registry.is_version_compatible("double", "1.0.0") is True
    assert registry.is_version_compatible("double", "2.0.0") is False


def test_public_metadata_excludes_handler_and_sensitive_default(test_settings):
    registry = ToolRegistry(test_settings)
    registry.register(definition())

    metadata = registry.metadata("double").model_dump(mode="json")

    assert "handler" not in metadata
    assert "sensitive_input_fields" not in metadata
    assert "password" in str(metadata["input_json_schema"])
    assert "secret-default" not in str(metadata)
