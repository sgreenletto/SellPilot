from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sellpilot.core.enums import (
    ConfirmationStatus,
    OperationStatus,
    ToolCallerType,
    ToolCallStatus,
    ToolRiskLevel,
)
from sellpilot.core.exceptions import UnauthenticatedError
from sellpilot.core.logging import redact_sensitive
from sellpilot.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from sellpilot.schemas.confirmation import ConfirmationTaskResponse
from sellpilot.schemas.operation_log import OperationLogResponse
from sellpilot.schemas.tool import ToolCallResponse
from sellpilot.tools.sanitization import audit_summary


def test_argon2_password_hash_and_verify():
    password_hash = hash_password("A-safe-test-password!")
    assert password_hash.startswith("$argon2")
    assert verify_password("A-safe-test-password!", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_jwt_contains_required_claims(test_settings):
    user_id = uuid4()
    token = create_access_token(
        user_id=user_id,
        username="admin",
        role="ADMIN",
        settings=test_settings,
    )
    payload = decode_access_token(token, test_settings)
    assert payload["sub"] == str(user_id)
    assert {"username", "role", "iat", "exp", "jti"}.issubset(payload)


def test_expired_jwt_is_rejected(test_settings):
    token = create_access_token(
        user_id=uuid4(),
        username="admin",
        role="ADMIN",
        settings=test_settings,
        expires_delta=timedelta(seconds=-1),
    )
    with pytest.raises(UnauthenticatedError):
        decode_access_token(token, test_settings)


def test_sensitive_values_are_redacted_from_log_messages():
    message = redact_sensitive(
        "password=secret token:abc API_KEY=value cookie=session partner_key=partner"
    )
    assert "secret" not in message
    assert "token:abc" not in message
    assert "API_KEY=value" not in message
    assert "cookie=session" not in message
    assert "partner_key=partner" not in message


def test_public_task_runtime_responses_recursively_redact_and_truncate():
    now = datetime.now(UTC)
    secret = "never-return-this-secret"
    nested = {
        "items": [{"Authorization": secret, "note": "x" * 5000}],
        "password": secret,
    }
    confirmation_id = uuid4()
    task_id = uuid4()
    confirmation = SimpleNamespace(
        id=confirmation_id,
        agent_task_id=task_id,
        task_step_id=None,
        operation_type="test.write",
        target_type="test",
        target_id="synthetic",
        risk_level=ToolRiskLevel.WRITE,
        before_snapshot=nested,
        after_snapshot=nested,
        status=ConfirmationStatus.PENDING,
        idempotency_key="safe-idempotency-key",
        created_by=uuid4(),
        confirmed_by=None,
        created_at=now,
        confirmed_at=None,
        execution_started_at=None,
        executed_at=None,
        execution_result=nested,
        error_message=f"password={secret}",
        risk_warning=f"token={secret}",
    )
    public_confirmation = ConfirmationTaskResponse.from_confirmation(
        confirmation,
        max_bytes=1024,
    ).model_dump_json()

    tool_call = SimpleNamespace(
        id=uuid4(),
        tool_name="test_tool",
        tool_version="1.0.0",
        risk_level=ToolRiskLevel.READ,
        caller_type=ToolCallerType.TEST,
        caller_name="pytest",
        request_id=str(uuid4()),
        user_id=uuid4(),
        task_id=task_id,
        task_step_id=None,
        confirmation_id=confirmation_id,
        input_summary=nested,
        output_summary=nested,
        attempt_history=nested,
        status=ToolCallStatus.SUCCEEDED,
        attempt_count=1,
        duration_ms=1,
        error_code=None,
        error_message=None,
        started_at=now,
        completed_at=now,
        created_at=now,
    )
    public_tool_call = ToolCallResponse.from_tool_call(
        tool_call,
        max_bytes=1024,
    ).model_dump_json()

    operation_log = SimpleNamespace(
        id=uuid4(),
        action="tool_completed",
        status=OperationStatus.SUCCEEDED,
        agent_task_id=task_id,
        task_step_id=None,
        tool_call_id=tool_call.id,
        confirmation_task_id=confirmation_id,
        actor_id=uuid4(),
        request_id=str(uuid4()),
        created_at=now,
        details=nested,
    )
    public_log = OperationLogResponse.from_operation_log(
        operation_log,
        max_bytes=1024,
    ).model_dump_json()

    combined = public_confirmation + public_tool_call + public_log
    assert secret not in combined
    assert "[REDACTED]" in combined
    assert "TRUNCATED" in combined or '"truncated":true' in combined


def test_audit_summary_limits_deep_and_large_collections():
    deep: dict[str, object] = {}
    cursor = deep
    for _ in range(20):
        child: dict[str, object] = {}
        cursor["child"] = child
        cursor = child
    cursor["items"] = list(range(200))

    summary = audit_summary(deep, max_bytes=16_384)
    encoded = str(summary)
    assert "TRUNCATED:MAX_DEPTH" in encoded
