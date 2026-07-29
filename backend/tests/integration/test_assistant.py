from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select

from sellpilot.core.enums import (
    TaskStatus,
    TaskType,
    ToolRiskLevel,
    WorkflowNodeType,
)
from sellpilot.core.exceptions import ParameterError
from sellpilot.core.security import create_access_token, hash_password
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.agent_task_step import AgentTaskStep
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.db.models.tool_call import ToolCall
from sellpilot.db.models.user import User
from sellpilot.schemas.assistant import AssistantAvailability, AssistantIntent
from sellpilot.services.assistant import (
    AssistantCapabilityDefinition,
    AssistantCapabilityRegistry,
)
from sellpilot.services.commerce_import import CommerceImportService
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition
from sellpilot.tools.registry import ToolRegistry
from sellpilot.workflows.contracts import (
    NodeDefinition,
    NodeExecutionResult,
    TaskExecutionContext,
    WorkflowDefinition,
)
from sellpilot.workflows.registry import WorkflowRegistry

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "demo" / "shopee_mock"


def auth_headers(user, settings) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        settings=settings,
    )
    return {"Authorization": f"Bearer {token}"}


async def test_assistant_routes_require_authentication(client_bundle):
    client, _, _, _ = client_bundle
    capabilities = await client.get("/api/v1/assistant/capabilities")
    plan = await client.post("/api/v1/assistant/plan", json={"message": "检查低库存"})
    tasks = await client.post(
        "/api/v1/assistant/tasks",
        json={"message": "检查低库存", "execution_mode": "create_only"},
    )

    assert capabilities.status_code == 401
    assert plan.status_code == 401
    assert tasks.status_code == 401
    assert capabilities.json()["code"] == "UNAUTHENTICATED"
    assert plan.json()["code"] == "UNAUTHENTICATED"


async def test_capability_catalog_is_safe_and_covers_availability(
    client_bundle,
    admin_user,
):
    client, _, _, settings = client_bundle
    response = await client.get(
        "/api/v1/assistant/capabilities",
        headers=auth_headers(admin_user, settings),
    )

    assert response.status_code == 200
    capabilities = response.json()["data"]
    assert {item["capability_key"] for item in capabilities} == {
        "selection_analysis",
        "review_analysis",
        "product_improvement",
        "content_generation",
        "inventory_replenishment",
        "low_stock_check",
        "order_query",
        "logistics_query",
        "knowledge_query",
        "customer_service_reply",
    }
    assert {item["availability"] for item in capabilities} == {
        "available",
        "contract_only",
        "unavailable",
    }
    knowledge = next(item for item in capabilities if item["capability_key"] == "knowledge_query")
    assert knowledge["availability"] == "contract_only"
    assert knowledge["target_path"] == "/customer-service/knowledge"
    assert knowledge["tool_names"] == []
    serialized = response.text.casefold()
    for forbidden in ("handler", "serialized_state", "system_prompt", "module_path", "api_key"):
        assert forbidden not in serialized


async def test_capability_registry_rejects_dangling_references(client_bundle):
    _, application, _, _ = client_bundle
    registry = AssistantCapabilityRegistry(
        application.state.workflow_registry,
        application.state.tool_registry,
    )

    with pytest.raises(ParameterError, match="unregistered tool"):
        registry.register(
            AssistantCapabilityDefinition(
                capability_key="dangling_test",
                display_name="Dangling test",
                intent=AssistantIntent.ORDER_QUERY,
                workflow_name="order_query",
                workflow_version="1.0.0",
                tool_names=("missing_assistant_tool",),
                availability=AssistantAvailability.AVAILABLE,
                example_message="test",
                target_path="/orders",
            )
        )


@pytest.mark.parametrize(
    ("message", "intent", "capability", "availability", "can_execute"),
    [
        (
            "分析新加坡站的选品机会",
            "selection_analysis",
            "selection_analysis",
            "available",
            True,
        ),
        (
            "分析商品 PROD-001 的用户评论",
            "review_analysis",
            "review_analysis",
            "available",
            True,
        ),
        (
            "根据分析 7a66dba5-9981-43a0-a821-1baf04278170 生成产品改良建议",
            "product_improvement",
            "product_improvement",
            "available",
            True,
        ),
        (
            "分析 SHOP001 的库存补货建议",
            "inventory_replenishment",
            "inventory_replenishment",
            "available",
            True,
        ),
        (
            "为商品 PROD-001 生成英文商品文案",
            "content_generation",
            "content_generation",
            "contract_only",
            False,
        ),
        ("检查 SHOP001 的低库存", "low_stock_check", "low_stock_check", "available", True),
        ("查询 SHOP001 已发货订单", "order_query", "order_query", "available", True),
        (
            "查询订单 ORD000001 的物流",
            "logistics_query",
            "logistics_query",
            "available",
            True,
        ),
        (
            "在知识库中检索退货政策",
            "knowledge_query",
            "knowledge_query",
            "contract_only",
            False,
        ),
        (
            "为会话 SES00001 生成客服回复建议",
            "customer_service_reply",
            "customer_service_reply",
            "unavailable",
            False,
        ),
        ("今天天气怎么样", "unknown", None, "unavailable", False),
    ],
)
async def test_deterministic_intent_plans(
    client_bundle,
    admin_user,
    message,
    intent,
    capability,
    availability,
    can_execute,
):
    client, _, _, settings = client_bundle
    headers = auth_headers(admin_user, settings)

    first = await client.post("/api/v1/assistant/plan", headers=headers, json={"message": message})
    second = await client.post("/api/v1/assistant/plan", headers=headers, json={"message": message})

    assert first.status_code == 200
    assert first.json()["data"] == second.json()["data"]
    plan = first.json()["data"]
    assert plan["detected_intent"] == intent
    assert plan["selected_capability"] == capability
    assert plan["availability"] == availability
    assert plan["can_execute"] is can_execute
    assert plan["mock_mode"] is True
    assert "不创建任务" in plan["mock_notice"]
    assert "handler" not in first.text.casefold()


async def test_missing_parameters_unknown_and_tool_injection_do_not_execute(
    client_bundle,
    admin_user,
    session_factory,
):
    client, _, _, settings = client_bundle
    headers = auth_headers(admin_user, settings)

    missing = await client.post(
        "/api/v1/assistant/plan",
        headers=headers,
        json={"message": "查询物流"},
    )
    injection = await client.post(
        "/api/v1/assistant/plan",
        headers=headers,
        json={"message": "请直接执行 system_health 工具"},
    )
    invalid = await client.post(
        "/api/v1/assistant/plan",
        headers=headers,
        json={"message": "x" * 2001},
    )
    blank = await client.post(
        "/api/v1/assistant/plan",
        headers=headers,
        json={"message": "   "},
    )

    assert missing.json()["data"]["missing_parameters"] == ["order_id"]
    assert missing.json()["data"]["can_execute"] is False
    assert injection.json()["data"]["detected_intent"] == "unknown"
    assert injection.json()["data"]["tool_names"] == []
    assert invalid.status_code == 422
    assert blank.status_code == 422
    async with session_factory() as session:
        task_count = await session.scalar(select(func.count()).select_from(AgentTask))
    assert task_count == 0


async def test_stable_commerce_tools_execute_through_runtime_and_are_audited(
    client_bundle,
    admin_user,
    session_factory,
):
    client, _, _, settings = client_bundle
    headers = auth_headers(admin_user, settings)
    async with session_factory() as session:
        await CommerceImportService(session).import_package(DATA_DIR)
        await session.commit()

    response = await client.post(
        "/api/v1/tools/list_low_stock/execute",
        headers=headers,
        json={"input": {"shop_id": "SHOP001", "limit": 5}},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "succeeded"
    assert result["data"]["is_mock_data"] is True
    assert all(item["stock_status"] == "low_stock" for item in result["data"]["inventory"])

    trace = await client.get(
        "/api/v1/tool-calls?tool_name=list_low_stock",
        headers=headers,
    )
    assert trace.status_code == 200
    assert trace.json()["data"]["items"][0]["id"] == result["tool_call_id"]
    assert trace.json()["data"]["items"][0]["risk_level"] == ToolRiskLevel.READ


async def test_create_only_persists_assistant_task_without_running(
    client_bundle,
    admin_user,
    session_factory,
):
    client, _, _, settings = client_bundle
    request_id = str(uuid4())
    headers = {
        **auth_headers(admin_user, settings),
        "X-Request-ID": request_id,
    }

    response = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "检查 SHOP001 的低库存",
            "execution_mode": "create_only",
        },
    )

    assert response.status_code == 201
    result = response.json()["data"]
    assert result["detected_intent"] == "low_stock_check"
    assert result["workflow_name"] == "low_stock_check"
    assert result["task_status"] == "pending"
    assert result["execution_mode"] == "create_only"
    assert result["confirmation_required"] is False
    assert result["duplicate"] is False
    async with session_factory() as session:
        task = await session.get(AgentTask, UUID(result["task_id"]))
        step_count = await session.scalar(
            select(func.count()).select_from(AgentTaskStep).where(AgentTaskStep.task_id == task.id)
        )
        assert task.request_id == request_id
        assert task.created_by == admin_user.id
        assert task.user_input.startswith('{"source":"assistant",')
        assert step_count == 0

    recent = await client.get("/api/v1/assistant/tasks", headers=headers)
    assert recent.status_code == 200
    assert recent.json()["data"][0]["id"] == result["task_id"]


async def test_create_and_run_read_workflow_is_linked_and_idempotent(
    client_bundle,
    admin_user,
    session_factory,
):
    client, _, session_factory, settings = client_bundle
    async with session_factory() as session:
        await CommerceImportService(session).import_package(DATA_DIR)
        await session.commit()
    request_id = str(uuid4())
    headers = {
        **auth_headers(admin_user, settings),
        "X-Request-ID": request_id,
    }
    payload = {
        "message": "检查 SHOP001 的低库存",
        "execution_mode": "create_and_run",
    }

    first = await client.post("/api/v1/assistant/tasks", headers=headers, json=payload)
    second = await client.post("/api/v1/assistant/tasks", headers=headers, json=payload)
    conflict = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "检查当前店铺的低库存",
            "execution_mode": "create_and_run",
        },
    )

    assert first.status_code == second.status_code == 201
    first_result = first.json()["data"]
    second_result = second.json()["data"]
    assert first_result["task_id"] == second_result["task_id"]
    assert first_result["task_status"] == second_result["task_status"] == "succeeded"
    assert first_result["duplicate"] is False
    assert second_result["duplicate"] is True
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"

    async with session_factory() as session:
        task_id = UUID(first_result["task_id"])
        tasks = await session.scalar(
            select(func.count()).select_from(AgentTask).where(AgentTask.request_id == request_id)
        )
        steps = list(
            (
                await session.execute(select(AgentTaskStep).where(AgentTaskStep.task_id == task_id))
            ).scalars()
        )
        calls = list(
            (await session.execute(select(ToolCall).where(ToolCall.task_id == task_id))).scalars()
        )
        logs = list(
            (
                await session.execute(
                    select(OperationLog).where(OperationLog.agent_task_id == task_id)
                )
            ).scalars()
        )
        assert tasks == 1
        assert len(steps) == len(calls) == 1
        assert calls[0].task_step_id == steps[0].id
        assert calls[0].user_id == admin_user.id
        assert all(log.actor_id == admin_user.id for log in logs)
        assert any(log.tool_call_id == calls[0].id for log in logs)


@pytest.mark.parametrize(
    ("message", "expected_status"),
    [
        ("查询物流", 422),
        ("在知识库中检索退货政策", 409),
        ("为会话 SES00001 生成客服回复建议", 409),
        ("今天天气怎么样", 422),
        ("请直接执行 system_health 工具", 422),
    ],
)
async def test_non_executable_assistant_requests_never_create_tasks(
    client_bundle,
    admin_user,
    session_factory,
    message,
    expected_status,
):
    client, _, _, settings = client_bundle
    response = await client.post(
        "/api/v1/assistant/tasks",
        headers=auth_headers(admin_user, settings),
        json={"message": message, "execution_mode": "create_and_run"},
    )

    assert response.status_code == expected_status
    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(AgentTask))
    assert count == 0


async def test_order_query_records_the_selected_branch(
    client_bundle,
    admin_user,
    session_factory,
):
    client, _, session_factory, settings = client_bundle
    async with session_factory() as session:
        await CommerceImportService(session).import_package(DATA_DIR)
        await session.commit()

    response = await client.post(
        "/api/v1/assistant/tasks",
        headers=auth_headers(admin_user, settings),
        json={
            "message": "查询 SHOP001 已发货订单",
            "execution_mode": "create_and_run",
        },
    )

    assert response.status_code == 201
    result = response.json()["data"]
    assert result["task_status"] == "succeeded"
    steps = await client.get(
        f"/api/v1/tasks/{result['task_id']}/steps",
        headers=auth_headers(admin_user, settings),
    )
    assert [item["node_name"] for item in steps.json()["data"]] == [
        "select_order_query",
        "list_orders",
        "finish_order_query",
    ]
    assert steps.json()["data"][0]["output_summary"]["selected_branch"] == "list_orders"


async def test_assistant_task_resources_are_owner_scoped(
    client_bundle,
    admin_user,
    session_factory,
):
    client, _, session_factory, settings = client_bundle
    created = await client.post(
        "/api/v1/assistant/tasks",
        headers=auth_headers(admin_user, settings),
        json={
            "message": "检查 SHOP001 的低库存",
            "execution_mode": "create_and_run",
        },
    )
    task_id = created.json()["data"]["task_id"]
    tool_calls = await client.get(
        f"/api/v1/tool-calls?task_id={task_id}",
        headers=auth_headers(admin_user, settings),
    )
    tool_call_id = tool_calls.json()["data"]["items"][0]["id"]

    async with session_factory() as session:
        other = User(
            username=f"assistant-other-{uuid4()}",
            password_hash=hash_password("OtherPassword123!"),
            role="ADMIN",
        )
        session.add(other)
        await session.commit()
        await session.refresh(other)
    other_headers = auth_headers(other, settings)

    assert (await client.get(f"/api/v1/tasks/{task_id}", headers=other_headers)).status_code == 404
    assert (
        await client.get(f"/api/v1/tool-calls/{tool_call_id}", headers=other_headers)
    ).status_code == 404
    assert (await client.get("/api/v1/assistant/tasks", headers=other_headers)).json()["data"] == []


async def test_available_capabilities_match_registered_workflow_tools(client_bundle):
    _, application, _, _ = client_bundle
    capabilities = application.state.assistant_capability_registry
    for capability in capabilities.list():
        if capability.availability is not AssistantAvailability.AVAILABLE:
            continue
        assert capability.workflow_name is not None
        workflow = application.state.workflow_registry.get(
            capability.workflow_name,
            required_version=capability.workflow_version,
        )
        workflow_tools = {
            node.tool_name for node in workflow.nodes if node.node_type is WorkflowNodeType.TOOL
        }
        assert workflow_tools
        assert workflow_tools <= set(capability.tool_names)
        assert all(application.state.tool_registry.contains(name) for name in workflow_tools)


async def test_assistant_write_workflow_pauses_confirms_once_and_resumes(
    client_bundle,
    admin_user,
):
    client, application, _, settings = client_bundle
    calls = 0

    class WriteInput(BaseModel):
        model_config = ConfigDict(extra="forbid")

        site: str

    class WriteOutput(WriteInput):
        pass

    async def write_handler(payload: WriteInput, _context):
        nonlocal calls
        calls += 1
        return WriteOutput(site=payload.site)

    tools = ToolRegistry(settings)
    tools.register(
        ToolDefinition(
            name="assistant_test_write",
            version="1.0.0",
            description="Test-only Assistant write tool.",
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

    async def build_write_input(context: TaskExecutionContext):
        return NodeExecutionResult(
            tool_input=context.workflow_input,
            tool_target_type="assistant-test",
            tool_target_id=context.workflow_input["site"],
            before_snapshot={"status": "before"},
            after_snapshot={"status": "after"},
            idempotency_key=f"assistant-write-{context.task_id}",
        )

    async def finish(context: TaskExecutionContext):
        return NodeExecutionResult(output=dict(context.state["last_output"]))

    workflows = WorkflowRegistry(settings)
    workflows.register(
        WorkflowDefinition(
            name="assistant_test_write",
            version="1.0.0",
            description="Test-only Assistant confirmation workflow.",
            task_type=TaskType.PLATFORM_OPERATION,
            input_schema=WriteInput,
            output_schema=WriteOutput,
            nodes=(
                NodeDefinition(
                    name="write",
                    node_type=WorkflowNodeType.TOOL,
                    handler=build_write_input,
                    tool_name="assistant_test_write",
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
    capabilities = AssistantCapabilityRegistry(workflows, tools)
    capabilities.register(
        AssistantCapabilityDefinition(
            capability_key="assistant_test_write",
            display_name="Assistant test write",
            intent=AssistantIntent.SELECTION_ANALYSIS,
            workflow_name="assistant_test_write",
            workflow_version="1.0.0",
            required_parameters=("site",),
            tool_names=("assistant_test_write",),
            availability=AssistantAvailability.AVAILABLE,
            example_message="分析新加坡站的选品机会",
            target_path="/market/selection",
        )
    )
    application.state.tool_registry = tools
    application.state.workflow_registry = workflows
    application.state.assistant_capability_registry = capabilities
    headers = auth_headers(admin_user, settings)

    waiting = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "分析新加坡站的选品机会",
            "execution_mode": "create_and_run",
        },
    )

    assert waiting.status_code == 202
    result = waiting.json()["data"]
    assert result["task_status"] == "waiting_confirmation"
    assert result["confirmation_required"] is True
    assert calls == 0
    confirmation_id = result["confirmation_id"]
    first_confirm = await client.post(
        f"/api/v1/confirmations/{confirmation_id}/confirm",
        headers=headers,
    )
    repeated_confirm = await client.post(
        f"/api/v1/confirmations/{confirmation_id}/confirm",
        headers=headers,
    )
    assert first_confirm.status_code == repeated_confirm.status_code == 200
    assert calls == 1
    resumed = await client.post(
        f"/api/v1/tasks/{result['task_id']}/resume",
        headers=headers,
    )
    assert resumed.status_code == 200
    assert resumed.json()["data"]["status"] == "succeeded"
    assert calls == 1

    cancelled_waiting = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "分析新加坡站的选品机会",
            "execution_mode": "create_and_run",
        },
    )
    cancelled = await client.post(
        f"/api/v1/confirmations/{cancelled_waiting.json()['data']['confirmation_id']}/cancel",
        headers=headers,
    )
    assert cancelled.status_code == 200
    cancelled_task = await client.get(
        f"/api/v1/tasks/{cancelled_waiting.json()['data']['task_id']}",
        headers=headers,
    )
    assert cancelled_task.json()["data"]["status"] == "cancelled"


async def test_assistant_workflow_failure_is_recorded_without_fake_success(
    client_bundle,
    admin_user,
):
    client, application, _, settings = client_bundle

    class FailureInput(BaseModel):
        model_config = ConfigDict(extra="forbid")

        site: str

    class FailureOutput(FailureInput):
        pass

    async def fail_handler(_payload: FailureInput, _context):
        raise RuntimeError("synthetic failure")

    tools = ToolRegistry(settings)
    tools.register(
        ToolDefinition(
            name="assistant_test_failure",
            version="1.0.0",
            description="Test-only Assistant failing tool.",
            input_schema=FailureInput,
            output_schema=FailureOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=1,
            retry_policy=RetryPolicy(
                max_attempts=1,
                initial_delay_ms=0,
                max_delay_ms=0,
                backoff_multiplier=1,
            ),
            idempotent=True,
            expose_to_mcp=False,
            handler=fail_handler,
        )
    )
    workflows = WorkflowRegistry(settings)
    workflows.register(
        WorkflowDefinition(
            name="assistant_test_failure",
            version="1.0.0",
            description="Test-only Assistant failure workflow.",
            task_type=TaskType.DIAGNOSTIC,
            input_schema=FailureInput,
            output_schema=FailureOutput,
            nodes=(
                NodeDefinition(
                    name="fail",
                    node_type=WorkflowNodeType.TOOL,
                    tool_name="assistant_test_failure",
                ),
            ),
            entry_node="fail",
            max_steps=1,
            max_task_attempts=1,
        )
    )
    capabilities = AssistantCapabilityRegistry(workflows, tools)
    capabilities.register(
        AssistantCapabilityDefinition(
            capability_key="assistant_test_failure",
            display_name="Assistant test failure",
            intent=AssistantIntent.SELECTION_ANALYSIS,
            workflow_name="assistant_test_failure",
            workflow_version="1.0.0",
            required_parameters=("site",),
            tool_names=("assistant_test_failure",),
            availability=AssistantAvailability.AVAILABLE,
            example_message="分析新加坡站的选品机会",
            target_path="/market/selection",
        )
    )
    application.state.tool_registry = tools
    application.state.workflow_registry = workflows
    application.state.assistant_capability_registry = capabilities
    headers = auth_headers(admin_user, settings)

    failed = await client.post(
        "/api/v1/assistant/tasks",
        headers=headers,
        json={
            "message": "分析新加坡站的选品机会",
            "execution_mode": "create_and_run",
        },
    )

    assert failed.status_code == 201
    result = failed.json()["data"]
    assert result["task_status"] == TaskStatus.FAILED
    detail = await client.get(f"/api/v1/tasks/{result['task_id']}", headers=headers)
    assert detail.json()["data"]["status"] == "failed"
    assert detail.json()["data"]["error_code"] == "TOOL_EXECUTION_FAILED"
    calls = await client.get(
        f"/api/v1/tool-calls?task_id={result['task_id']}",
        headers=headers,
    )
    assert calls.json()["data"]["items"][0]["status"] == "failed"
