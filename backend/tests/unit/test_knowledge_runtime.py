from sellpilot.tools.knowledge import build_knowledge_tools
from sellpilot.workflows.runtime import build_knowledge_query_definition


def test_knowledge_runtime_allows_bounded_cold_model_startup(test_settings) -> None:
    tool = build_knowledge_tools()[0]
    workflow = build_knowledge_query_definition(test_settings)

    assert tool.name == "search_knowledge"
    assert tool.timeout_seconds == 90
    assert workflow.nodes[0].tool_name == "search_knowledge"
    assert workflow.nodes[0].timeout_seconds == 90
