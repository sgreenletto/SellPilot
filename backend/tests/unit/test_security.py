from datetime import timedelta
from uuid import uuid4

import pytest

from sellpilot.core.exceptions import UnauthenticatedError
from sellpilot.core.logging import redact_sensitive
from sellpilot.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


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
    message = redact_sensitive("password=secret token:abc API_KEY=value")
    assert "secret" not in message
    assert "token:abc" not in message
    assert "API_KEY=value" not in message
