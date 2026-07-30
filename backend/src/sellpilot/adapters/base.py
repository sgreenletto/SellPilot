from abc import ABC, abstractmethod
from typing import Any

from sellpilot.schemas.platform import PlatformPingResult


class PlatformAdapter(ABC):
    """平台能力的统一契约。

    上层 Service 依赖本抽象，而不是依赖 MockShopeeAdapter。真实平台接入时，
    新适配器负责认证、字段转换和平台异常映射，上层业务调用方式保持一致。
    """

    # 平台状态：用于明确区分可运行的 Mock 与尚未接入的真实平台 Stub。
    @abstractmethod
    async def ping(self) -> PlatformPingResult: ...

    @abstractmethod
    async def get_capabilities(self) -> list[str]: ...

    # 商品、价格与库存能力。
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

    # 订单与履约能力。
    @abstractmethod
    async def list_orders(self, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_order(self, order_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_logistics(self, order_id: str) -> dict[str, Any]: ...

    # 评论与客服消息能力。
    @abstractmethod
    async def list_reviews(self, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def list_messages(self, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def send_message(self, payload: dict[str, Any]) -> dict[str, Any]: ...
