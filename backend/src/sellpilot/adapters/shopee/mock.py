from typing import Any, Never

from sellpilot.adapters.base import PlatformAdapter
from sellpilot.core.exceptions import PlatformFeatureNotImplementedError
from sellpilot.schemas.platform import PlatformPingResult


class MockShopeeAdapter(PlatformAdapter):
    async def ping(self) -> PlatformPingResult:
        return PlatformPingResult(
            adapter="mock",
            configured=True,
            reachable=True,
            message="Mock adapter foundation is available",
        )

    async def get_capabilities(self) -> list[str]:
        return ["system.ping", "platform.contracts"]

    def _not_implemented(self, feature: str) -> Never:
        raise PlatformFeatureNotImplementedError(
            f"Mock Shopee business feature '{feature}' is not implemented in the foundation phase"
        )

    async def list_products(self, **filters: Any) -> list[dict[str, Any]]:
        self._not_implemented("list_products")

    async def get_product(self, product_id: str) -> dict[str, Any]:
        self._not_implemented("get_product")

    async def create_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._not_implemented("create_product")

    async def update_product(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._not_implemented("update_product")

    async def publish_product(self, product_id: str) -> dict[str, Any]:
        self._not_implemented("publish_product")

    async def unpublish_product(self, product_id: str) -> dict[str, Any]:
        self._not_implemented("unpublish_product")

    async def update_price(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._not_implemented("update_price")

    async def update_inventory(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._not_implemented("update_inventory")

    async def list_orders(self, **filters: Any) -> list[dict[str, Any]]:
        self._not_implemented("list_orders")

    async def get_order(self, order_id: str) -> dict[str, Any]:
        self._not_implemented("get_order")

    async def get_logistics(self, order_id: str) -> dict[str, Any]:
        self._not_implemented("get_logistics")

    async def list_messages(self, **filters: Any) -> list[dict[str, Any]]:
        self._not_implemented("list_messages")

    async def send_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._not_implemented("send_message")
