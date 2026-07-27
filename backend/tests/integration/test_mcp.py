from sellpilot.mcp_server.server import mcp, system_health


async def test_mcp_server_exposes_only_system_health():
    tools = await mcp.list_tools()
    assert [tool.name for tool in tools] == ["system_health"]
    result = await system_health()
    assert result["app_version"] == "0.1.0"
    assert result["status"] == "ok"
