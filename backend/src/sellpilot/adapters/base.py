from abc import ABC, abstractmethod
from typing import Any

from sellpilot.schemas.platform import PlatformPingResult


class PlatformAdapter(ABC):
    @abstractmethod
    async def ping(self) -> PlatformPingResult: ...

    @abstractmethod
    async def get_capabilities(self) -> list[str]: ...

    @abstractmethod
    async def list_products(self, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_product(self, product_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def create_product(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def update_product(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def publish_product(self, product_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def unpublish_product(self, product_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def update_price(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def update_inventory(
        self, product_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def list_orders(self, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_order(self, order_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_logistics(self, order_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def list_messages(self, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def send_message(self, payload: dict[str, Any]) -> dict[str, Any]: ...
