from typing import Any

from mcp.server.fastmcp import FastMCP

from sellpilot.core.config import get_settings
from sellpilot.core.exceptions import ToolFailureError
from sellpilot.tools.contracts import ToolContext
from sellpilot.tools.registry import ToolRegistry
from sellpilot.tools.system import build_system_health_tool

settings = get_settings()
tool_registry = ToolRegistry()
tool_registry.register(build_system_health_tool(settings))
mcp = FastMCP(
    name="SellPilot Foundation",
    instructions="Read-only public backend foundation diagnostics.",
    log_level=settings.log_level,
)


@mcp.tool(
    name="system_health",
    description="Return non-sensitive SellPilot foundation service status.",
    structured_output=True,
)
async def system_health() -> dict[str, Any]:
    result = await tool_registry.invoke("system_health", {}, ToolContext())
    if not result.success or result.data is None:
        raise ToolFailureError(result.error_message or "system_health failed")
    return result.data


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
