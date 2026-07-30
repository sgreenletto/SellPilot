from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.adapters.factory import create_platform_adapter
from sellpilot.core.config import Settings
from sellpilot.db.models.commerce import (
    InventoryRecord,
    Order,
    Product,
    ReturnRefund,
    Sku,
)
from sellpilot.services.commerce_normalization import normalize_product_external_id


class CommerceQueryService:
    """平台查询应用服务。

    核心平台查询通过 PlatformAdapter 转发；Service 负责应用层参数处理，
    不直接依赖 MockShopeeAdapter 的具体类型。
    """

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.adapter = create_platform_adapter(settings, session)

    async def list_products(self, **filters: Any) -> list[dict[str, Any]]:
        return await self.adapter.list_products(**filters)

    async def get_product(self, product_id: str) -> dict[str, Any]:
        return await self.adapter.get_product(normalize_product_external_id(product_id))

    async def list_skus(
        self,
        *,
        product_id: str | None,
        status: str | None,
        seller_sku: str | None,
        offset: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        statement = (
            select(Sku, Product.external_id)
            .join(Product, Sku.product_id == Product.id)
            .order_by(Sku.seller_sku.asc(), Sku.external_id.asc())
        )
        if product_id:
            statement = statement.where(Product.external_id == product_id)
        if status:
            statement = statement.where(Sku.status == status)
        if seller_sku:
            statement = statement.where(Sku.seller_sku == seller_sku)
        rows = (await self.session.execute(statement.offset(offset).limit(limit))).all()
        return [
            {
                "sku_id": sku.external_id,
                "product_id": current_product_id,
                "seller_sku": sku.seller_sku,
                "variation_name": sku.variation_name,
                "variation_value": sku.variation_value,
                "price": sku.price,
                "cost": sku.cost,
                "weight": sku.weight,
                "status": sku.status,
                "updated_at": sku.source_updated_at,
                "is_mock_data": sku.is_mock_data,
            }
            for sku, current_product_id in rows
        ]

    async def list_orders(self, **filters: Any) -> list[dict[str, Any]]:
        return await self.adapter.list_orders(**filters)

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await self.adapter.get_order(order_id)

    async def get_logistics(self, order_id: str) -> dict[str, Any]:
        # 物流通过稳定 order_id 获取，确保订单详情与履约上下文指向同一对象。
        return await self.adapter.get_logistics(order_id)

    async def list_reviews(self, **filters: Any) -> list[dict[str, Any]]:
        if product_id := filters.get("product_id"):
            filters["product_id"] = normalize_product_external_id(str(product_id))
        return await self.adapter.list_reviews(**filters)

    async def list_messages(self, **filters: Any) -> list[dict[str, Any]]:
        # 客服上层读取统一消息结构，不依赖 Mock 会话表的具体字段。
        return await self.adapter.list_messages(**filters)

    async def list_inventory(
        self,
        *,
        status: str | None,
        offset: int,
        limit: int,
        shop_id: str | None = None,
    ) -> list[dict[str, Any]]:
        statement = (
            select(InventoryRecord, Sku.external_id, Product.external_id)
            .join(Sku, InventoryRecord.sku_id == Sku.id)
            .join(Product, Sku.product_id == Product.id)
            .order_by(InventoryRecord.updated_at.desc())
        )
        if status:
            statement = statement.where(InventoryRecord.stock_status == status)
        if shop_id:
            statement = statement.where(Product.source_shop_external_id == shop_id)
        rows = (await self.session.execute(statement.offset(offset).limit(limit))).all()
        return [
            {
                "inventory_id": inventory.external_id,
                "sku_id": sku_id,
                "product_id": product_id,
                "warehouse_id": inventory.warehouse_external_id,
                "available_stock": inventory.available_stock,
                "reserved_stock": inventory.reserved_stock,
                "safety_stock": inventory.safety_stock,
                "stock_status": inventory.stock_status,
                "updated_at": inventory.source_updated_at,
                "is_mock_data": inventory.is_mock_data,
            }
            for inventory, sku_id, product_id in rows
        ]

    async def list_returns(
        self, *, status: str | None, offset: int, limit: int
    ) -> list[dict[str, Any]]:
        statement = (
            select(ReturnRefund, Order.external_id)
            .join(Order, ReturnRefund.order_id == Order.id)
            .order_by(ReturnRefund.requested_at.desc())
        )
        if status:
            statement = statement.where(ReturnRefund.status == status)
        rows = (await self.session.execute(statement.offset(offset).limit(limit))).all()
        return [
            {
                "return_id": record.external_id,
                "order_id": order_id,
                "request_type": record.request_type,
                "reason_type": record.reason_type,
                "amount": record.amount,
                "status": record.status,
                "requested_at": record.requested_at,
                "completed_at": record.completed_at,
                "is_mock_data": record.is_mock_data,
            }
            for record, order_id in rows
        ]
