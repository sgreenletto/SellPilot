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


class CommerceQueryService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.adapter = create_platform_adapter(settings, session)

    async def list_products(self, **filters: Any) -> list[dict[str, Any]]:
        return await self.adapter.list_products(**filters)

    async def get_product(self, product_id: str) -> dict[str, Any]:
        return await self.adapter.get_product(product_id)

    async def list_orders(self, **filters: Any) -> list[dict[str, Any]]:
        return await self.adapter.list_orders(**filters)

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await self.adapter.get_order(order_id)

    async def get_logistics(self, order_id: str) -> dict[str, Any]:
        return await self.adapter.get_logistics(order_id)

    async def list_messages(self, **filters: Any) -> list[dict[str, Any]]:
        return await self.adapter.list_messages(**filters)

    async def list_inventory(
        self, *, status: str | None, offset: int, limit: int
    ) -> list[dict[str, Any]]:
        statement = (
            select(InventoryRecord, Sku.external_id, Product.external_id)
            .join(Sku, InventoryRecord.sku_id == Sku.id)
            .join(Product, Sku.product_id == Product.id)
            .order_by(InventoryRecord.updated_at.desc())
        )
        if status:
            statement = statement.where(InventoryRecord.stock_status == status)
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
