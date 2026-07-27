from uuid import UUID, uuid4

from fastapi import Request

from sellpilot.core.enums import ConfirmationStatus, ToolRiskLevel
from sellpilot.core.response import ApiResponse
from sellpilot.core.security import create_access_token, hash_password
from sellpilot.db.models.user import User
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.services.task import TaskService
from tests.conftest import TEST_PASSWORD


async def add_user(session_factory, *, active: bool = True) -> User:
    async with session_factory() as session:
        user = User(
            username=f"user-{uuid4()}",
            password_hash=hash_password(TEST_PASSWORD),
            role="ADMIN",
            is_active=active,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def login(client, user: User, password: str = TEST_PASSWORD):
    return await client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
    )


async def test_live_health_does_not_need_database(client_bundle):
    client, _, _, _ = client_bundle
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["data"] == {"status": "ok"}


async def test_ready_health_executes_database_query(client_bundle):
    client, _, _, _ = client_bundle
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["data"]["database"] == "reachable"


async def test_request_id_matches_header_and_body(client_bundle):
    client, _, _, _ = client_bundle
    request_id = str(uuid4())
    response = await client.get("/api/v1/health/live", headers={"X-Request-ID": request_id})
    assert response.headers["X-Request-ID"] == request_id
    assert response.json()["request_id"] == request_id


async def test_invalid_request_id_is_replaced_with_uuid(client_bundle):
    client, _, _, _ = client_bundle
    response = await client.get("/api/v1/health/live", headers={"X-Request-ID": "not-a-uuid"})
    assert UUID(response.headers["X-Request-ID"])
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


async def test_oversized_request_id_is_replaced_with_uuid(client_bundle):
    client, _, _, _ = client_bundle
    response = await client.get("/api/v1/health/live", headers={"X-Request-ID": "a" * 1000})
    assert UUID(response.headers["X-Request-ID"])
    assert len(response.headers["X-Request-ID"]) == 36


async def test_validation_exception_uses_uniform_response(client_bundle):
    client, _, _, _ = client_bundle
    response = await client.post("/api/v1/auth/login", json={})
    body = response.json()
    assert response.status_code == 422
    assert body["code"] == "PARAMETER_ERROR"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["data"] == [
        {
            "field": "body.username",
            "message": "Field required",
            "type": "missing",
        },
        {
            "field": "body.password",
            "message": "Field required",
            "type": "missing",
        },
    ]


async def test_validation_error_does_not_echo_sensitive_input(client_bundle):
    client, _, _, _ = client_bundle
    secret = "super-secret-password-value"
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "valid-name", "password": secret * 20},
    )
    assert response.status_code == 422
    assert secret not in response.text
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


async def test_login_me_and_change_password(client_bundle):
    client, _, session_factory, _ = client_bundle
    user = await add_user(session_factory)
    login_response = await login(client, user)
    token = login_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["data"]["username"] == user.username

    change_response = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "old_password": TEST_PASSWORD,
            "new_password": "A-new-secure-password!",
        },
    )
    assert change_response.status_code == 200
    assert (await login(client, user)).status_code == 401
    assert (await login(client, user, "A-new-secure-password!")).status_code == 200


async def test_disabled_user_cannot_login(client_bundle):
    client, _, session_factory, _ = client_bundle
    user = await add_user(session_factory, active=False)
    response = await login(client, user)
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


async def test_platform_status_reports_mock_boundary(client_bundle):
    client, _, _, _ = client_bundle
    response = await client.get("/api/v1/platform/status")
    assert response.status_code == 200
    assert response.json()["data"] == {
        "adapter": "mock",
        "configured": True,
        "reachable": True,
        "message": "Mock adapter foundation is available",
        "capabilities": ["system.ping", "platform.contracts"],
    }


async def test_unhandled_exception_does_not_leak_stack(client_bundle):
    client, application, _, _ = client_bundle

    @application.get("/test-unhandled", response_model=ApiResponse[dict])
    async def unhandled(request: Request):
        raise RuntimeError("sensitive internal details")

    response = await client.get("/test-unhandled")
    body = response.json()
    assert response.status_code == 500
    assert body["code"] == "INTERNAL_ERROR"
    assert "sensitive internal details" not in response.text
    assert "traceback" not in response.text.lower()


async def test_tasks_endpoint_requires_bearer_token(client_bundle):
    client, _, _, _ = client_bundle
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 401


async def test_authenticated_task_list_is_paginated(client_bundle):
    client, _, session_factory, settings = client_bundle
    user = await add_user(session_factory)
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        settings=settings,
    )
    response = await client.get(
        "/api/v1/tasks?page=1&page_size=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 10,
        "pages": 0,
    }


async def test_confirmation_without_executor_returns_error_and_stays_pending(
    client_bundle,
):
    client, _, session_factory, settings = client_bundle
    user = await add_user(session_factory)
    async with session_factory() as session:
        task = await TaskService(session).create_internal_task(
            task_type="diagnostic", user_input="test", created_by=user.id
        )
        confirmation = await ConfirmationService(session).create(
            agent_task_id=task.id,
            operation_type="unregistered.write",
            target_type="test-target",
            target_id="target-1",
            risk_level=ToolRiskLevel.WRITE,
            idempotency_key=str(uuid4()),
            created_by=user.id,
        )
        confirmation_id = confirmation.id
        await session.commit()

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        settings=settings,
    )
    response = await client.post(
        f"/api/v1/confirmations/{confirmation_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "CONFIRMATION_EXECUTOR_NOT_FOUND"

    async with session_factory() as session:
        stored = await ConfirmationService(session).get(confirmation_id)
        assert stored.status == ConfirmationStatus.PENDING
