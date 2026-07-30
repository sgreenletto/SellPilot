from argparse import Namespace

import pytest

from sellpilot.cli import start_api
from sellpilot.cli.start_api import EndpointState
from sellpilot.core.config import Settings


def _settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        API_HOST=overrides.get("API_HOST", "127.0.0.1"),
        API_PORT=overrides.get("API_PORT", 8000),
    )


def test_healthy_sellpilot_is_reused_without_binding(monkeypatch) -> None:
    settings = _settings()
    monkeypatch.setattr(start_api, "is_sellpilot_healthy", lambda _settings: True)

    def unexpected_bind(_settings):
        raise AssertionError("a healthy SellPilot endpoint must be reused")

    monkeypatch.setattr(start_api, "port_is_bindable", unexpected_bind)

    assert start_api.inspect_endpoint(settings) is EndpointState.SELLPILOT_RUNNING


def test_unknown_port_owner_is_reported_without_starting_uvicorn(
    monkeypatch,
    capsys,
) -> None:
    settings = _settings()
    monkeypatch.setattr(start_api, "get_settings", lambda: settings)
    monkeypatch.setattr(
        start_api,
        "parse_args",
        lambda: Namespace(print_proxy_target=False, reload=False),
    )
    monkeypatch.setattr(start_api, "is_sellpilot_healthy", lambda _settings: False)
    monkeypatch.setattr(start_api, "port_is_bindable", lambda _settings: False)
    monkeypatch.setattr(
        start_api.uvicorn,
        "run",
        lambda *_args, **_kwargs: pytest.fail("Uvicorn must not start on an occupied port"),
    )

    with pytest.raises(SystemExit) as exc_info:
        start_api.main()

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "已被其他进程占用" in captured.err
    assert "不会自动终止任何进程" in captured.err


def test_configured_port_drives_backend_and_frontend_proxy_target() -> None:
    settings = _settings(API_PORT=8123)

    assert start_api.proxy_target(settings) == "http://127.0.0.1:8123"
    assert start_api.health_url(settings) == "http://127.0.0.1:8123/api/v1/health/live"


def test_free_endpoint_starts_on_configured_loopback_address(monkeypatch) -> None:
    settings = _settings(API_PORT=8124)
    captured = {}
    monkeypatch.setattr(start_api, "get_settings", lambda: settings)
    monkeypatch.setattr(
        start_api,
        "parse_args",
        lambda: Namespace(print_proxy_target=False, reload=False),
    )
    monkeypatch.setattr(
        start_api,
        "inspect_endpoint",
        lambda _settings: EndpointState.AVAILABLE,
    )
    monkeypatch.setattr(
        start_api.uvicorn,
        "run",
        lambda app, **kwargs: captured.update(app=app, **kwargs),
    )

    start_api.main()

    assert captured == {
        "app": "sellpilot.main:app",
        "host": "127.0.0.1",
        "port": 8124,
        "reload": False,
        "log_level": "info",
    }
