from typing import Any, Never

from sellpilot.adapters.base import PlatformAdapter
from sellpilot.core.exceptions import PlatformNotConfiguredError
from sellpilot.schemas.platform import PlatformPingResult


class RealShopeeAdapterStub(PlatformAdapter):
    """真实 Shopee 接口骨架，当前不联网、不读取密钥、也不具备业务能力。

    所有业务方法明确抛出未配置错误，目的是固定未来接入边界，并防止系统在
    real 模式失败时静默使用 Mock 数据。
    """

    async def ping(self) -> PlatformPingResult:
        return PlatformPingResult(
            adapter="real",
            configured=False,
            reachable=False,
            message="Real Shopee integration is not implemented or connected",
        )

    async def get_capabilities(self) -> list[str]:
        return []

    def _not_configured(self) -> Never:
        raise PlatformNotConfiguredError(
            "Real Shopee adapter is a non-networking stub and is not configured"
        )

    async def list_products(self, **filters: Any) -> list[dict[str, Any]]:
        self._not_configured()

    async def get_product(self, product_id: str) -> dict[str, Any]:
        self._not_configured()

    async def create_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._not_configured()

    async def update_product(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._not_configured()

    async def publish_product(self, product_id: str) -> dict[str, Any]:
        self._not_configured()

    async def unpublish_product(self, product_id: str) -> dict[str, Any]:
        self._not_configured()

    async def update_price(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._not_configured()

    async def update_inventory(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._not_configured()

    async def list_orders(self, **filters: Any) -> list[dict[str, Any]]:
        self._not_configured()

    async def get_order(self, order_id: str) -> dict[str, Any]:
        self._not_configured()

    async def get_logistics(self, order_id: str) -> dict[str, Any]:
        self._not_configured()

    async def list_reviews(self, **filters: Any) -> list[dict[str, Any]]:
        self._not_configured()

    async def list_messages(self, **filters: Any) -> list[dict[str, Any]]:
        self._not_configured()

    async def send_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._not_configured()
