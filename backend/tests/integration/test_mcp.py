from sqlalchemy import select

from sellpilot.core.enums import ToolCallerType, ToolCallStatus
from sellpilot.db.models.tool_call import ToolCall
from sellpilot.mcp_server import server


async def test_mcp_server_exposes_only_system_health_and_uses_runtime(
    session_factory,
):
    original_provider = server.mcp_bridge.session_factory_provider
    server.mcp_bridge.session_factory_provider = lambda: session_factory
    tools = await server.mcp.list_tools()
    assert [tool.name for tool in tools] == ["system_health"]
    try:
        result = await server.system_health()
        assert result["app_version"] == "0.5.0"
        assert result["status"] == "ok"
    finally:
        server.mcp_bridge.session_factory_provider = original_provider

    async with session_factory() as session:
        tool_call = (await session.scalars(select(ToolCall))).one()
        assert tool_call.tool_name == "system_health"
        assert tool_call.caller_type == ToolCallerType.MCP
        assert tool_call.status == ToolCallStatus.SUCCEEDED
        assert tool_call.request_id
