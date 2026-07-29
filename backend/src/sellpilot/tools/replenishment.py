from sellpilot.core.enums import ToolRiskLevel
from sellpilot.core.exceptions import ParameterError
from sellpilot.schemas.replenishment import (
    ReplenishmentAnalysisOutput,
    ReplenishmentAnalysisRequest,
)
from sellpilot.services.replenishment import ReplenishmentService
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition, ToolExecutionContext
from sellpilot.tools.registry import ToolRegistry


async def _analyze(
    payload: ReplenishmentAnalysisRequest,
    context: ToolExecutionContext,
) -> ReplenishmentAnalysisOutput:
    if context.session is None:
        raise ParameterError("replenishment analysis requires a database session")
    return await ReplenishmentService(context.session).analyze(payload)


def build_replenishment_tool() -> ToolDefinition:
    return ToolDefinition(
        name="analyze_inventory_replenishment",
        version="1.0.0",
        description=(
            "Analyze shop SKU inventory and recent order demand, then return deterministic "
            "replenishment recommendations without changing inventory."
        ),
        input_schema=ReplenishmentAnalysisRequest,
        output_schema=ReplenishmentAnalysisOutput,
        risk_level=ToolRiskLevel.READ,
        timeout_seconds=30,
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_delay_ms=0,
            max_delay_ms=0,
            backoff_multiplier=1,
        ),
        idempotent=True,
        expose_to_mcp=False,
        handler=_analyze,
    )


def register_replenishment_tools(registry: ToolRegistry) -> None:
    registry.register(build_replenishment_tool())
