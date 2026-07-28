from pydantic import BaseModel, ConfigDict

from sellpilot.core.config import Settings
from sellpilot.core.enums import ToolRiskLevel
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition, ToolExecutionContext


class SystemHealthInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SystemHealthOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_name: str
    app_version: str
    environment: str
    adapter: str
    status: str


def build_system_health_tool(settings: Settings) -> ToolDefinition:
    async def system_health(_: BaseModel, context: ToolExecutionContext) -> SystemHealthOutput:
        return SystemHealthOutput(
            app_name=settings.app_name,
            app_version=settings.app_version,
            environment=settings.app_env,
            adapter=settings.platform_adapter,
            status="ok",
        )

    return ToolDefinition(
        name="system_health",
        version="1.0.0",
        description="Return non-sensitive SellPilot foundation service status",
        input_schema=SystemHealthInput,
        output_schema=SystemHealthOutput,
        risk_level=ToolRiskLevel.READ,
        timeout_seconds=2.0,
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_delay_ms=0,
            max_delay_ms=0,
            backoff_multiplier=1,
        ),
        idempotent=True,
        expose_to_mcp=True,
        enabled=True,
        handler=system_health,
    )
