from pydantic import BaseModel

from sellpilot.core.config import Settings
from sellpilot.core.enums import ToolRiskLevel
from sellpilot.tools.contracts import ToolContext, ToolDefinition


class SystemHealthInput(BaseModel):
    pass


class SystemHealthOutput(BaseModel):
    app_name: str
    app_version: str
    environment: str
    adapter: str
    status: str


def build_system_health_tool(settings: Settings) -> ToolDefinition:
    async def system_health(_: BaseModel, context: ToolContext) -> SystemHealthOutput:
        return SystemHealthOutput(
            app_name=settings.app_name,
            app_version=settings.app_version,
            environment=settings.app_env,
            adapter=settings.platform_adapter,
            status="ok",
        )

    return ToolDefinition(
        name="system_health",
        description="Return non-sensitive SellPilot foundation service status",
        input_schema=SystemHealthInput,
        output_schema=SystemHealthOutput,
        risk_level=ToolRiskLevel.READ,
        requires_confirmation=False,
        timeout_seconds=2.0,
        handler=system_health,
    )
