import pytest

from sellpilot.core.exceptions import DuplicateOperationError, ResourceNotFoundError
from sellpilot.workflows.diagnostic import build_diagnostic_workflow
from sellpilot.workflows.registry import WorkflowRegistry


def state(*, force_retry: bool, max_retries: int = 2) -> dict:
    return {
        "task_id": "diagnostic-task",
        "task_type": "diagnostic",
        "user_input": "foundation test",
        "current_step": "",
        "context": {"force_retry": force_retry},
        "tool_results": [],
        "messages": [],
        "retry_count": 0,
        "max_retries": max_retries,
        "requires_confirmation": False,
        "confirmation_id": None,
        "result": None,
        "error_code": None,
        "error_message": None,
    }


def test_workflow_registry_register_get_list_and_errors():
    registry = WorkflowRegistry()
    workflow = object()
    registry.register("diagnostic", workflow)
    assert registry.get("diagnostic") is workflow
    assert registry.list() == ["diagnostic"]
    with pytest.raises(DuplicateOperationError):
        registry.register("diagnostic", object())
    with pytest.raises(ResourceNotFoundError):
        registry.get("missing")


async def test_diagnostic_workflow_success_branch_passes_state():
    result = await build_diagnostic_workflow().ainvoke(state(force_retry=False))
    assert result["current_step"] == "finalize"
    assert result["result"] == {"status": "ok", "diagnostic": True, "finalized": True}
    assert result["retry_count"] == 0


async def test_diagnostic_workflow_retry_loop_is_bounded():
    result = await build_diagnostic_workflow().ainvoke(state(force_retry=True, max_retries=2))
    assert result["current_step"] == "finalize"
    assert result["retry_count"] == 2
    assert result["error_code"] == "DIAGNOSTIC_MAX_RETRIES"
    assert result["result"]["status"] == "failed"
