import pytest
from pydantic import ValidationError

from sellpilot.adapters.factory import create_platform_adapter
from sellpilot.adapters.shopee.mock import MockShopeeAdapter
from sellpilot.adapters.shopee.real_stub import RealShopeeAdapterStub
from sellpilot.core.config import Settings
from sellpilot.core.exceptions import (
    PlatformFeatureNotImplementedError,
    PlatformNotConfiguredError,
)


def test_adapter_factory_selects_mock(test_settings):
    assert isinstance(create_platform_adapter(test_settings), MockShopeeAdapter)


def test_adapter_factory_real_mode_never_silently_falls_back():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, PLATFORM_ADAPTER="real")


async def test_mock_adapter_foundation_status_and_unimplemented_business_method():
    adapter = MockShopeeAdapter()
    ping = await adapter.ping()
    assert ping.configured is True
    assert ping.reachable is True
    assert await adapter.get_capabilities() == ["system.ping", "platform.contracts"]
    with pytest.raises(PlatformFeatureNotImplementedError):
        await adapter.list_products()


async def test_real_stub_is_unconfigured_and_never_calls_network():
    adapter = RealShopeeAdapterStub()
    ping = await adapter.ping()
    assert ping.configured is False
    assert ping.reachable is False
    with pytest.raises(PlatformNotConfiguredError):
        await adapter.get_order("not-a-real-order")
