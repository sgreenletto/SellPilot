from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.adapters.base import PlatformAdapter
from sellpilot.adapters.shopee.mock import MockShopeeAdapter
from sellpilot.adapters.shopee.real_stub import RealShopeeAdapterStub
from sellpilot.core.config import Settings
from sellpilot.core.exceptions import PlatformNotConfiguredError


def create_platform_adapter(
    settings: Settings, session: AsyncSession | None = None
) -> PlatformAdapter:
    """根据配置创建统一平台适配器，业务层无需判断具体实现类型。

    real 模式只返回不会联网的 Stub；未配置真实接入时绝不静默回退到 Mock，
    避免把模拟数据误报为真实平台数据。
    """
    if settings.platform_adapter == "mock":
        return MockShopeeAdapter(session)
    if settings.platform_adapter == "real":
        return RealShopeeAdapterStub()
    raise PlatformNotConfiguredError(f"Unsupported platform adapter '{settings.platform_adapter}'")
