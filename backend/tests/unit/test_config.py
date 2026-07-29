import pytest
from pydantic import ValidationError

from sellpilot.core.config import REPOSITORY_ROOT, Settings, clear_settings_cache, get_settings


def test_settings_use_only_repository_root_env_file() -> None:
    assert Settings.model_config["env_file"] == REPOSITORY_ROOT / ".env"


def test_settings_accept_database_url_without_enforcing_a_driver() -> None:
    settings = Settings(_env_file=None, DATABASE_URL="sqlite+aiosqlite:///sellpilot.db")

    assert settings.database_url == "sqlite+aiosqlite:///sellpilot.db"


def test_settings_environment_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "TestPilot")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://sellpilot:test@localhost:5432/settings_test",
    )
    monkeypatch.setenv("JWT_SECRET_KEY", "safe-test-secret-with-more-than-32-characters")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173"]')
    settings = Settings(_env_file=None)
    assert settings.app_name == "TestPilot"
    assert settings.cors_origins == ["http://localhost:5173"]


def test_platform_adapter_rejects_unknown_value():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, PLATFORM_ADAPTER="other")


def test_real_mode_requires_explicit_configuration():
    with pytest.raises(ValidationError, match="never falls back to mock"):
        Settings(_env_file=None, PLATFORM_ADAPTER="real")


def test_tool_timeout_and_retry_settings_validate_cross_field_limits():
    with pytest.raises(ValidationError, match="default timeout"):
        Settings(
            _env_file=None,
            TOOL_DEFAULT_TIMEOUT_SECONDS=31,
            TOOL_MAX_TIMEOUT_SECONDS=30,
        )
    with pytest.raises(ValidationError, match="initial delay"):
        Settings(
            _env_file=None,
            TOOL_RETRY_INITIAL_DELAY_MS=1001,
            TOOL_RETRY_MAX_DELAY_MS=1000,
        )
    with pytest.raises(ValidationError):
        Settings(_env_file=None, TOOL_READ_MAX_ATTEMPTS=4)


def test_task_runtime_settings_enforce_hard_limits():
    with pytest.raises(ValidationError, match="Task default node timeout"):
        Settings(
            _env_file=None,
            TASK_DEFAULT_NODE_TIMEOUT_SECONDS=61,
            TASK_MAX_NODE_TIMEOUT_SECONDS=60,
        )
    with pytest.raises(ValidationError):
        Settings(_env_file=None, TASK_MAX_STEPS=201)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, TASK_MAX_ATTEMPTS=6)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, TASK_STATE_MAX_BYTES=100)


@pytest.mark.parametrize("secret", ["replace_me", "replace_with_at_least_32_random_characters"])
def test_production_rejects_example_jwt_secret(secret):
    with pytest.raises(ValidationError, match="Production requires"):
        Settings(_env_file=None, APP_ENV="production", JWT_SECRET_KEY=secret)


def test_settings_factory_cache_can_be_cleared(monkeypatch):
    clear_settings_cache()
    monkeypatch.setenv("APP_NAME", "First")
    first = get_settings()
    monkeypatch.setenv("APP_NAME", "Second")
    assert get_settings() is first
    clear_settings_cache()
    assert get_settings().app_name == "Second"
    clear_settings_cache()
