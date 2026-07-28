from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from sellpilot.core.enums import TaskType, ToolRiskLevel, WorkflowNodeType
from sellpilot.core.security import create_access_token, hash_password
from sellpilot.db.models.user import User
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition
from sellpilot.workflows.contracts import (
    NodeDefinition,
    NodeExecutionResult,
    TaskExecutionContext,
    WorkflowDefinition,
)


def auth_headers(user: User, settings, *, request_id: str | None = None) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        settings=settings,
    )
    headers = {"Authorization": f"Bearer {token}"}
    if request_id is not None:
        headers["X-Request-ID"] = request_id
    return headers


async def test_task_api_requires_authentication(client_bundle):
    client, _, _, _ = client_bundle
    for method, path in (
        ("GET", "/api/v1/tasks"),
        ("POST", "/api/v1/tasks"),
        ("GET", "/api/v1/tasks/workflows"),
    ):
        response = await client.request(method, path, json={} if method == "POST" else None)
        assert response.status_code == 401


async def test_diagnostic_task_api_create_run_steps_rerun_and_cancel(
    client_bundle,
    admin_user,
):
    client, _, _, settings = client_bundle
    request_id = str(uuid4())
    headers = auth_headers(admin_user, settings, request_id=request_id)
    create_response = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "workflow_name": "diagnostic",
            "workflow_input": {"message": "api-ok"},
        },
    )
    assert create_response.status_code == 201
    assert create_response.headers["X-Request-ID"] == request_id
    assert create_response.json()["request_id"] == request_id
    task = create_response.json()["data"]
    assert task["status"] == "pending"
    assert "user_input" not in task
    assert "serialized_state" not in task

    run_request_id = str(uuid4())
    run_response = await client.post(
        f"/api/v1/tasks/{task['id']}/run",
        headers=auth_headers(admin_user, settings, request_id=run_request_id),
    )
    assert run_response.status_code == 200
    assert run_response.json()["data"]["status"] == "succeeded"
    assert run_response.json()["data"]["result"]["message"] == "api-ok"
    assert run_response.headers["X-Request-ID"] == run_request_id
    assert run_response.json()["request_id"] == run_request_id
    assert run_response.json()["data"]["request_id"] == run_request_id

    steps_response = await client.get(
        f"/api/v1/tasks/{task['id']}/steps",
        headers=headers,
    )
    assert steps_response.status_code == 200
    steps = steps_response.json()["data"]
    assert len(steps) == 1
    assert steps[0]["sequence"] == 1
    assert steps[0]["status"] == "succeeded"

    rerun_response = await client.post(
        f"/api/v1/tasks/{task['id']}/rerun",
        headers=headers,
    )
    assert rerun_response.status_code == 201
    rerun = rerun_response.json()["data"]
    assert rerun["parent_task_id"] == task["id"]
    assert rerun["status"] == "pending"
    cancel_response = await client.post(
        f"/api/v1/tasks/{rerun['id']}/cancel",
        headers=headers,
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["data"]["status"] == "cancelled"
    repeat_cancel = await client.post(
        f"/api/v1/tasks/{rerun['id']}/cancel",
        headers=headers,
    )
    assert repeat_cancel.status_code == 409
    assert repeat_cancel.json()["code"] == "TASK_CANCEL_NOT_ALLOWED"


async def test_system_health_workflow_creates_linked_tool_call(client_bundle, admin_user):
    client, _, _, settings = client_bundle
    headers = auth_headers(admin_user, settings)
    created = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"workflow_name": "system_health_check", "workflow_input": {}},
    )
    assert created.status_code == 201
    task_id = created.json()["data"]["id"]
    executed = await client.post(
        f"/api/v1/tasks/{task_id}/run",
        headers=headers,
    )
    assert executed.status_code == 200
    assert executed.json()["data"]["result"]["status"] == "ok"

    calls = await client.get(
        f"/api/v1/tool-calls?task_id={task_id}",
        headers=headers,
    )
    assert calls.status_code == 200
    assert calls.json()["data"]["total"] == 1
    assert calls.json()["data"]["items"][0]["tool_name"] == "system_health"
    steps = await client.get(f"/api/v1/tasks/{task_id}/steps", headers=headers)
    assert steps.json()["data"][0]["tool_call_id"] == calls.json()["data"]["items"][0]["id"]


async def test_task_api_validation_not_found_conflict_and_owner_isolation(
    client_bundle,
    admin_user,
):
    client, _, session_factory, settings = client_bundle
    headers = auth_headers(admin_user, settings)
    invalid = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "workflow_name": "diagnostic",
            "workflow_input": {"message": "x" * 201},
        },
    )
    assert invalid.status_code == 422
    assert "x" * 201 not in invalid.text
    missing_workflow = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"workflow_name": "missing_workflow", "workflow_input": {}},
    )
    assert missing_workflow.status_code == 404
    missing = await client.get(f"/api/v1/tasks/{uuid4()}", headers=headers)
    assert missing.status_code == 404

    created = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"workflow_name": "diagnostic", "workflow_input": {"message": "owner"}},
    )
    task_id = created.json()["data"]["id"]
    async with session_factory() as session:
        other = User(
            username=f"other-{uuid4()}",
            password_hash=hash_password("OtherPassword123!"),
            role="ADMIN",
        )
        session.add(other)
        await session.commit()
        await session.refresh(other)
    other_headers = auth_headers(other, settings)
    assert (await client.get(f"/api/v1/tasks/{task_id}", headers=other_headers)).status_code == 404
    assert (
        await client.post(f"/api/v1/tasks/{task_id}/run", headers=other_headers)
    ).status_code == 404

    first_run = await client.post(f"/api/v1/tasks/{task_id}/run", headers=headers)
    assert first_run.status_code == 200
    second_run = await client.post(f"/api/v1/tasks/{task_id}/run", headers=headers)
    assert second_run.status_code == 409
    assert second_run.json()["code"] == "TASK_NOT_RUNNABLE"

    listing = await client.get(
        "/api/v1/tasks?page=1&page_size=10&status=succeeded&workflow_name=diagnostic",
        headers=headers,
    )
    assert listing.status_code == 200
    assert listing.json()["data"]["pages"] == 1
    assert listing.json()["data"]["total"] >= 1


async def test_task_api_confirmation_pause_confirm_and_resume(
    client_bundle,
    admin_user,
):
    client, application, _, settings = client_bundle
    calls = 0

    class WriteInput(BaseModel):
        model_config = ConfigDict(extra="forbid")

        value: int

    class WriteOutput(WriteInput):
        pass

    async def write_handler(payload: WriteInput, _context):
        nonlocal calls
        calls += 1
        return WriteOutput(value=payload.value)

    application.state.tool_registry.register(
        ToolDefinition(
            name="api_test_write",
            version="1.0.0",
            description="Test-only API write",
            input_schema=WriteInput,
            output_schema=WriteOutput,
            risk_level=ToolRiskLevel.WRITE,
            timeout_seconds=1,
            retry_policy=RetryPolicy(
                max_attempts=1,
                initial_delay_ms=0,
                max_delay_ms=0,
                backoff_multiplier=1,
            ),
            idempotent=True,
            expose_to_mcp=False,
            handler=write_handler,
        )
    )

    async def build_input(context: TaskExecutionContext):
        return NodeExecutionResult(
            tool_input=context.workflow_input,
            tool_target_type="api-test",
            tool_target_id="target",
            idempotency_key=f"api-write-{context.task_id}",
        )

    async def finish(context: TaskExecutionContext):
        return NodeExecutionResult(output=dict(context.state["last_output"]))

    application.state.workflow_registry.register(
        WorkflowDefinition(
            name="api_write_confirmation",
            version="1.0.0",
            description="Test-only API confirmation workflow",
            task_type=TaskType.DIAGNOSTIC,
            input_schema=WriteInput,
            output_schema=WriteOutput,
            nodes=(
                NodeDefinition(
                    name="write",
                    node_type=WorkflowNodeType.TOOL,
                    handler=build_input,
                    tool_name="api_test_write",
                    next_node="finish",
                ),
                NodeDefinition(
                    name="finish",
                    node_type=WorkflowNodeType.FINISH,
                    handler=finish,
                ),
            ),
            entry_node="write",
            max_steps=2,
            max_task_attempts=1,
        )
    )
    headers = auth_headers(admin_user, settings)
    created = await client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"workflow_name": "api_write_confirmation", "workflow_input": {"value": 5}},
    )
    task_id = created.json()["data"]["id"]
    waiting = await client.post(f"/api/v1/tasks/{task_id}/run", headers=headers)
    assert waiting.status_code == 202
    result = waiting.json()["data"]
    assert result["confirmation_required"] is True
    assert calls == 0
    pending_resume = await client.post(
        f"/api/v1/tasks/{task_id}/resume",
        headers=headers,
    )
    assert pending_resume.status_code == 409
    assert pending_resume.json()["code"] == "TASK_CONFIRMATION_PENDING"

    confirmed = await client.post(
        f"/api/v1/confirmations/{result['confirmation_id']}/confirm",
        headers=headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["data"]["status"] == "succeeded"
    assert calls == 1
    resumed = await client.post(f"/api/v1/tasks/{task_id}/resume", headers=headers)
    assert resumed.status_code == 200
    assert resumed.json()["data"]["result"] == {"value": 5}
    assert calls == 1
