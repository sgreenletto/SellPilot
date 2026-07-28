from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from sellpilot.core.enums import ToolRiskLevel
from sellpilot.core.security import hash_password
from sellpilot.db.models.user import User
from sellpilot.services.task import TaskService
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition
from tests.conftest import TEST_PASSWORD


async def add_user(session_factory) -> User:
    async with session_factory() as session:
        user = User(
            username=f"tool-api-{uuid4()}",
            password_hash=hash_password(TEST_PASSWORD),
            role="ADMIN",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def auth_headers(client, session_factory):
    user = await add_user(session_factory)
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": TEST_PASSWORD},
    )
    return user, {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


async def test_tool_routes_require_authentication(client_bundle):
    client, _, _, _ = client_bundle
    for method, path in [
        ("GET", "/api/v1/tools"),
        ("GET", "/api/v1/tools/system_health"),
        ("POST", "/api/v1/tools/system_health/execute"),
        ("GET", "/api/v1/tool-calls"),
    ]:
        response = await client.request(method, path, json={"input": {}})
        assert response.status_code == 401
        assert response.json()["code"] == "UNAUTHENTICATED"


async def test_tool_metadata_and_not_found_are_safe(client_bundle):
    client, _, session_factory, _ = client_bundle
    _, headers = await auth_headers(client, session_factory)

    listing = await client.get("/api/v1/tools", headers=headers)
    assert listing.status_code == 200
    tools = listing.json()["data"]
    assert [item["name"] for item in tools] == [
        "analyze_product_reviews",
        "calculate_product_profit",
        "compare_products",
        "export_product_analysis_report",
        "get_product_reviews",
        "score_product_opportunity",
        "search_market_products",
        "system_health",
    ]
    assert tools[0]["risk_level"] == "read"
    assert tools[0]["confirmation_required"] is False
    assert "handler" not in listing.text
    assert "module" not in listing.text

    detail = await client.get("/api/v1/tools/system_health", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["version"] == "1.0.0"

    missing = await client.get("/api/v1/tools/not_registered", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["code"] == "TOOL_NOT_FOUND"


async def test_read_execute_and_tool_call_pagination_are_audited(client_bundle):
    client, _, session_factory, _ = client_bundle
    _, headers = await auth_headers(client, session_factory)
    request_id = str(uuid4())

    executed = await client.post(
        "/api/v1/tools/system_health/execute",
        headers={**headers, "X-Request-ID": request_id},
        json={"input": {}},
    )
    assert executed.status_code == 200
    body = executed.json()
    assert body["request_id"] == request_id
    assert executed.headers["X-Request-ID"] == request_id
    assert body["data"]["status"] == "succeeded"
    assert body["data"]["data"]["status"] == "ok"
    tool_call_id = body["data"]["tool_call_id"]

    listing = await client.get(
        "/api/v1/tool-calls?page=1&page_size=1&tool_name=system_health",
        headers=headers,
    )
    assert listing.status_code == 200
    page = listing.json()["data"]
    assert page["page"] == 1
    assert page["page_size"] == 1
    assert page["total"] == 1
    assert page["pages"] == 1
    assert page["items"][0]["id"] == tool_call_id
    assert "authorization" not in listing.text.lower()

    detail = await client.get(f"/api/v1/tool-calls/{tool_call_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["request_id"] == request_id
    missing = await client.get(f"/api/v1/tool-calls/{uuid4()}", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["code"] == "RESOURCE_NOT_FOUND"


async def test_selection_read_tool_uses_unified_executor_and_audit(client_bundle):
    client, _, session_factory, _ = client_bundle
    _, headers = await auth_headers(client, session_factory)
    request_id = str(uuid4())

    executed = await client.post(
        "/api/v1/tools/calculate_product_profit/execute",
        headers={**headers, "X-Request-ID": request_id},
        json={
            "input": {
                "candidate": {
                    "product_id": "SELECTION-TOOL-001",
                    "site": "sg",
                    "currency": "SGD",
                    "source": {
                        "source_type": "mock",
                        "source_name": "selection_tool_test",
                        "source_reference": "SELECTION-TOOL-001",
                        "is_mock": True,
                    },
                    "price": "50",
                    "cost": "20",
                    "shipping_cost": "5",
                    "platform_fee_rate": "0.10",
                }
            }
        },
    )

    assert executed.status_code == 200
    body = executed.json()
    assert body["request_id"] == request_id
    assert body["data"]["tool_name"] == "calculate_product_profit"
    assert body["data"]["status"] == "succeeded"
    assert body["data"]["data"]["profit"]["profit"] == "20.00"

    listing = await client.get(
        "/api/v1/tool-calls?tool_name=calculate_product_profit",
        headers=headers,
    )
    assert listing.status_code == 200
    tool_call = listing.json()["data"]["items"][0]
    assert tool_call["id"] == body["data"]["tool_call_id"]
    assert tool_call["caller_type"] == "api"
    assert tool_call["request_id"] == request_id


async def test_tool_input_validation_is_safe(client_bundle):
    client, _, session_factory, _ = client_bundle
    _, headers = await auth_headers(client, session_factory)
    secret = "must-not-be-returned"
    response = await client.post(
        "/api/v1/tools/system_health/execute",
        headers=headers,
        json={"input": {"unexpected": secret}},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "TOOL_INPUT_INVALID"
    assert secret not in response.text
    assert "Traceback" not in response.text


class WriteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int


class WriteOutput(BaseModel):
    result: int


async def test_write_api_returns_202_without_executing_handler(client_bundle):
    client, application, session_factory, _ = client_bundle
    user, headers = await auth_headers(client, session_factory)
    calls = 0

    async def handler(payload, _context):
        nonlocal calls
        calls += 1
        return {"result": payload.value}

    application.state.tool_registry.register(
        ToolDefinition(
            name="test_write_tool",
            version="1.0.0",
            description="Test-only write tool",
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
            handler=handler,
        )
    )
    async with session_factory() as session:
        task = await TaskService(session).create_internal_task(
            task_type="diagnostic",
            user_input="API confirmation",
            created_by=user.id,
        )
        await session.commit()
        task_id = task.id

    response = await client.post(
        "/api/v1/tools/test_write_tool/execute",
        headers=headers,
        json={
            "input": {"value": 3},
            "task_id": str(task_id),
            "idempotency_key": f"api-{uuid4()}",
            "target_type": "test",
            "target_id": "3",
        },
    )
    assert response.status_code == 202
    assert response.json()["data"]["confirmation_required"] is True
    confirmation_id = response.json()["data"]["confirmation_id"]
    assert confirmation_id
    assert calls == 0

    confirmed = await client.post(
        f"/api/v1/confirmations/{confirmation_id}/confirm",
        headers=headers,
    )
    repeated = await client.post(
        f"/api/v1/confirmations/{confirmation_id}/confirm",
        headers=headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["data"]["status"] == "succeeded"
    assert repeated.json()["data"]["status"] == "succeeded"
    assert calls == 1
