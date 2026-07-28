from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.adapters.base import PlatformAdapter
from sellpilot.adapters.shopee.mock import MockShopeeAdapter
from sellpilot.adapters.shopee.real_stub import RealShopeeAdapterStub
from sellpilot.core.config import Settings
from sellpilot.core.exceptions import PlatformNotConfiguredError


def create_platform_adapter(
    settings: Settings, session: AsyncSession | None = None
) -> PlatformAdapter:
    if settings.platform_adapter == "mock":
        return MockShopeeAdapter(session)
    if settings.platform_adapter == "real":
        return RealShopeeAdapterStub()
    raise PlatformNotConfiguredError(f"Unsupported platform adapter '{settings.platform_adapter}'")
