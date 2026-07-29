"""Start the local API without racing an already healthy SellPilot process."""

from __future__ import annotations

import argparse
import json
import socket
import sys
from enum import StrEnum
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import uvicorn

from sellpilot.core.config import Settings, get_settings


class EndpointState(StrEnum):
    AVAILABLE = "available"
    SELLPILOT_RUNNING = "sellpilot_running"
    OCCUPIED = "occupied"


def health_url(settings: Settings) -> str:
    return f"http://{settings.api_host}:{settings.api_port}{settings.api_v1_prefix}/health/live"


def proxy_target(settings: Settings) -> str:
    return f"http://{settings.api_host}:{settings.api_port}"


def is_sellpilot_healthy(settings: Settings, *, timeout_seconds: float = 1.5) -> bool:
    try:
        with urlopen(health_url(settings), timeout=timeout_seconds) as response:  # noqa: S310
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return False
    return (
        isinstance(payload, dict)
        and payload.get("code") == 0
        and isinstance(payload.get("data"), dict)
        and payload["data"].get("status") == "ok"
    )


def port_is_bindable(settings: Settings) -> bool:
    family = socket.AF_INET6 if ":" in settings.api_host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.bind((settings.api_host, settings.api_port))
    except OSError:
        return False
    return True


def inspect_endpoint(settings: Settings) -> EndpointState:
    if is_sellpilot_healthy(settings):
        return EndpointState.SELLPILOT_RUNNING
    if port_is_bindable(settings):
        return EndpointState.AVAILABLE
    return EndpointState.OCCUPIED


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the SellPilot development API")
    parser.add_argument(
        "--print-proxy-target",
        action="store_true",
        help="Print the configured frontend proxy target and exit",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable Uvicorn reload for explicit backend-only development",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    if args.print_proxy_target:
        print(proxy_target(settings))
        return

    state = inspect_endpoint(settings)
    if state is EndpointState.SELLPILOT_RUNNING:
        print(f"SellPilot 后端已健康运行，复用 {health_url(settings)}。")
        return
    if state is EndpointState.OCCUPIED:
        print(
            (
                f"无法启动 SellPilot：{settings.api_host}:{settings.api_port} "
                "已被其他进程占用，且健康检查未识别为 SellPilot。"
                "请检查占用进程，或通过 API_PORT 与 VITE_PROXY_TARGET 选择其他端口；"
                "启动器不会自动终止任何进程。"
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)

    uvicorn.run(
        "sellpilot.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=args.reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
