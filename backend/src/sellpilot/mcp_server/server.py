from collections.abc import Callable
from uuid import uuid4

from mcp.server.fastmcp import FastMCP
from pydantic import JsonValue
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sellpilot.core.config import get_settings
from sellpilot.core.enums import ToolCallerType, ToolCallStatus
from sellpilot.core.exceptions import ToolFailureError
from sellpilot.db.session import get_session_factory
from sellpilot.tools.contracts import ToolExecutionContext
from sellpilot.tools.executor import ToolExecutor
from sellpilot.tools.runtime import build_tool_registry

settings = get_settings()
tool_registry = build_tool_registry(settings)
SessionFactoryProvider = Callable[[], async_sessionmaker[AsyncSession]]


class MCPToolBridge:
    """Thin MCP adapter; all validation, risk, retry and audit stays in ToolExecutor."""

    def __init__(
        self,
        session_factory_provider: SessionFactoryProvider = get_session_factory,
    ) -> None:
        self.session_factory_provider = session_factory_provider

    async def execute(
        self,
        name: str,
        payload: dict[str, JsonValue],
        *,
        request_id: str | None = None,
    ) -> dict[str, JsonValue]:
        tool_registry.get_mcp(name)
        async with self.session_factory_provider()() as session:
            try:
                result = await ToolExecutor(tool_registry, session, settings).execute(
                    name,
                    payload,
                    ToolExecutionContext(
                        request_id=request_id or str(uuid4()),
                        caller_type=ToolCallerType.MCP,
                        caller_name="sellpilot_mcp",
                    ),
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        if result.status is not ToolCallStatus.SUCCEEDED or result.data is None:
            raise ToolFailureError(result.error_message or "MCP tool execution failed")
        return result.data


mcp_bridge = MCPToolBridge()
mcp = FastMCP(
    name="SellPilot Foundation",
    instructions="Registry-filtered tools executed through the audited SellPilot runtime.",
    log_level=settings.log_level,
)


if tool_registry.contains("system_health") and any(
    definition.name == "system_health" for definition in tool_registry.list_mcp()
):

    @mcp.tool(
        name="system_health",
        description="Return non-sensitive SellPilot foundation service status.",
        structured_output=True,
    )
    async def system_health() -> dict[str, JsonValue]:
        return await mcp_bridge.execute("system_health", {})


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
