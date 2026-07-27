import pytest
from pydantic import ValidationError

from sellpilot.core.config import Settings, clear_settings_cache, get_settings


def test_settings_environment_override(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_NAME", "TestPilot")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'settings.db'}")
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
