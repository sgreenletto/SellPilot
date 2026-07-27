from typing import Literal

from langgraph.graph import END, START, StateGraph

from sellpilot.agents.state import BaseAgentState


def _initialize(state: BaseAgentState) -> dict[str, object]:
    return {
        "current_step": "initialize",
        "error_code": None,
        "error_message": None,
    }


def _validate(state: BaseAgentState) -> dict[str, object]:
    return {"current_step": "validate"}


def _validation_route(state: BaseAgentState) -> Literal["success", "retry", "failed"]:
    force_retry = bool(state["context"].get("force_retry"))
    if not force_retry:
        return "success"
    if state["retry_count"] >= state["max_retries"]:
        return "failed"
    return "retry"


def _retry(state: BaseAgentState) -> dict[str, object]:
    return {
        "current_step": "retry",
        "retry_count": state["retry_count"] + 1,
    }


def _success(state: BaseAgentState) -> dict[str, object]:
    return {
        "current_step": "success",
        "result": {"status": "ok", "diagnostic": True},
    }


def _failed(state: BaseAgentState) -> dict[str, object]:
    return {
        "current_step": "failed",
        "error_code": "DIAGNOSTIC_MAX_RETRIES",
        "error_message": "Diagnostic validation reached the configured retry limit",
        "result": {"status": "failed", "diagnostic": True},
    }


def _finalize(state: BaseAgentState) -> dict[str, object]:
    result = dict(state.get("result") or {})
    result["finalized"] = True
    return {"current_step": "finalize", "result": result}


def build_diagnostic_workflow():
    """Build a deterministic, no-LLM graph used only for foundation verification."""
    graph = StateGraph(BaseAgentState)
    graph.add_node("initialize", _initialize)
    graph.add_node("validate", _validate)
    graph.add_node("retry", _retry)
    graph.add_node("success", _success)
    graph.add_node("failed", _failed)
    graph.add_node("finalize", _finalize)

    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "validate")
    graph.add_conditional_edges(
        "validate",
        _validation_route,
        {"success": "success", "retry": "retry", "failed": "failed"},
    )
    graph.add_edge("retry", "validate")
    graph.add_edge("success", "finalize")
    graph.add_edge("failed", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(name="sellpilot_diagnostic")
