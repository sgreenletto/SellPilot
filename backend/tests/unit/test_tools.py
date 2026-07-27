import asyncio

import pytest
from pydantic import BaseModel

from sellpilot.core.enums import RiskLevel
from sellpilot.core.exceptions import DuplicateOperationError
from sellpilot.tools.contracts import ToolContext, ToolDefinition
from sellpilot.tools.registry import ToolRegistry


class NumberInput(BaseModel):
    value: int


class NumberOutput(BaseModel):
    doubled: int


async def double_handler(payload: BaseModel, context: ToolContext) -> NumberOutput:
    await asyncio.sleep(0)
    validated = NumberInput.model_validate(payload)
    return NumberOutput(doubled=validated.value * 2)


def definition(
    *,
    name: str = "double",
    risk_level: RiskLevel = RiskLevel.READ,
    timeout: float = 1,
    handler=double_handler,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Test tool",
        input_schema=NumberInput,
        output_schema=NumberOutput,
        risk_level=risk_level,
        requires_confirmation=risk_level is not RiskLevel.READ,
        timeout_seconds=timeout,
        handler=handler,
    )


def test_tool_registry_rejects_duplicate_names():
    registry = ToolRegistry()
    registry.register(definition())
    with pytest.raises(DuplicateOperationError):
        registry.register(definition())


async def test_tool_registry_validates_input_and_output():
    registry = ToolRegistry()
    registry.register(definition())
    invalid = await registry.invoke("double", {"value": "invalid"}, ToolContext())
    valid = await registry.invoke("double", {"value": 4}, ToolContext())
    assert invalid.success is False
    assert invalid.error_code == "TOOL_SCHEMA_VALIDATION_FAILED"
    assert valid.data == {"doubled": 8}


async def test_tool_registry_validates_output_schema():
    async def invalid_output(payload: BaseModel, context: ToolContext):
        await asyncio.sleep(0)
        return {"unexpected": True}

    registry = ToolRegistry()
    registry.register(definition(handler=invalid_output))
    result = await registry.invoke("double", {"value": 4}, ToolContext())
    assert result.success is False
    assert result.error_code == "TOOL_SCHEMA_VALIDATION_FAILED"


async def test_tool_registry_enforces_timeout():
    async def slow_handler(payload: BaseModel, context: ToolContext) -> NumberOutput:
        await asyncio.sleep(0.05)
        return NumberOutput(doubled=0)

    registry = ToolRegistry()
    registry.register(definition(timeout=0.001, handler=slow_handler))
    result = await registry.invoke("double", {"value": 1}, ToolContext())
    assert result.success is False
    assert result.error_code == "TOOL_TIMEOUT"


@pytest.mark.parametrize("risk_level", [RiskLevel.WRITE, RiskLevel.HIGH_RISK])
async def test_write_and_high_risk_tools_require_confirmation(risk_level):
    called = False

    async def guarded_handler(payload: BaseModel, context: ToolContext) -> NumberOutput:
        nonlocal called
        called = True
        return NumberOutput(doubled=0)

    registry = ToolRegistry()
    registry.register(definition(risk_level=risk_level, handler=guarded_handler))
    result = await registry.invoke("double", {"value": 1}, ToolContext())
    assert result.error_code == "TOOL_CONFIRMATION_REQUIRED"
    assert called is False
