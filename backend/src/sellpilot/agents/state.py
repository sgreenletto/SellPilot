from typing import Any, TypedDict


class BaseAgentState(TypedDict):
    task_id: str
    task_type: str
    user_input: str
    current_step: str
    context: dict[str, Any]
    tool_results: list[dict[str, Any]]
    messages: list[dict[str, Any]]
    retry_count: int
    max_retries: int
    requires_confirmation: bool
    confirmation_id: str | None
    result: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
