from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.commerce import InventoryRecord, Order, OrderItem, Product, Sku


@dataclass(frozen=True)
class ReplenishmentSourceRow:
    """补货公式所需的最小 SKU 数据快照。"""

    product_id: str
    product_title: str
    sku_id: str
    seller_sku: str
    site: str
    available_stock: int
    safety_stock: int
    units_sold: int
    is_mock_data: bool


class ReplenishmentRepository:
    """只负责从 PostgreSQL 聚合库存和销量，不在查询层计算补货建议。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_source_rows(
        self,
        *,
        shop_external_id: str,
        sales_since: datetime,
    ) -> list[ReplenishmentSourceRow]:
        # 一个 SKU 可能有多条仓库记录，先按 SKU 汇总可用库存和安全库存。
        inventory = (
            select(
                InventoryRecord.sku_id.label("sku_id"),
                func.coalesce(func.sum(InventoryRecord.available_stock), 0).label(
                    "available_stock"
                ),
                func.coalesce(func.sum(InventoryRecord.safety_stock), 0).label("safety_stock"),
                func.bool_and(InventoryRecord.is_mock_data).label("inventory_is_mock"),
            )
            .group_by(InventoryRecord.sku_id)
            .subquery()
        )
        # 只统计指定店铺、分析窗口内且未取消订单的有效销量。
        sales = (
            select(
                OrderItem.sku_id.label("sku_id"),
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
                func.bool_and(OrderItem.is_mock_data).label("sales_is_mock"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.source_shop_external_id == shop_external_id,
                Order.source_created_at >= sales_since,
                Order.order_status != "cancelled",
            )
            .group_by(OrderItem.sku_id)
            .subquery()
        )
        statement: Select[tuple[object, ...]] = (
            select(
                Product.external_id,
                Product.title,
                Sku.external_id,
                Sku.seller_sku,
                Product.site,
                inventory.c.available_stock,
                inventory.c.safety_stock,
                func.coalesce(sales.c.units_sold, 0),
                (
                    Product.is_mock_data
                    & Sku.is_mock_data
                    & inventory.c.inventory_is_mock
                    & func.coalesce(sales.c.sales_is_mock, True)
                ),
            )
            .join(Sku, Sku.product_id == Product.id)
            .join(inventory, inventory.c.sku_id == Sku.id)
            # 使用外连接保留近期零销量 SKU；其销量随后通过 coalesce 归零。
            .outerjoin(sales, sales.c.sku_id == Sku.id)
            .where(Product.source_shop_external_id == shop_external_id)
            .order_by(Sku.seller_sku)
        )
        rows = (await self.session.execute(statement)).all()
        return [
            ReplenishmentSourceRow(
                product_id=str(row[0]),
                product_title=str(row[1]),
                sku_id=str(row[2]),
                seller_sku=str(row[3]),
                site=str(row[4]),
                available_stock=int(row[5]),
                safety_stock=int(row[6]),
                units_sold=int(row[7]),
                is_mock_data=bool(row[8]),
            )
            for row in rows
        ]
