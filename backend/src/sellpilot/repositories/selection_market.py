from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import asc, case, desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.commerce import (
    CategoryTrend,
    InventoryRecord,
    LogisticsRecord,
    OrderItem,
    Product,
    ReturnRefund,
    Sku,
)
from sellpilot.schemas.selection import SelectionCandidateQuery

SITE_NAMES = {
    "sg": "Singapore",
    "my": "Malaysia",
    "ph": "Philippines",
    "th": "Thailand",
    "vn": "Vietnam",
    "id": "Indonesia",
}

RISKY_LOGISTICS_STATUSES = {"delayed", "exception", "failed", "lost", "returned"}
ACTIVE_SKU_STATUSES = {"active", "published"}


@dataclass(frozen=True)
class SelectionOperationalSignals:
    logistics_risk_rate: Decimal | None
    after_sales_rate: Decimal | None
    factory_fit_score: Decimal | None


class SelectionMarketRepository:
    """Read-only projection over imported Mock Shopee commerce data."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_candidates(
        self, query: SelectionCandidateQuery
    ) -> list[tuple[Product, CategoryTrend | None]]:
        site_name = SITE_NAMES.get(query.site.value)
        if site_name is None:
            return []
        predicates = [Product.site == site_name]
        if query.category_id:
            predicates.append(Product.category_external_id == query.category_id)
        if query.product_ids:
            predicates.append(Product.external_id.in_(query.product_ids))
        if query.min_price is not None:
            predicates.append(Product.price >= query.min_price)
        if query.max_price is not None:
            predicates.append(Product.price <= query.max_price)
        sort_column = getattr(Product, query.sort_by)
        ordering = desc(sort_column) if query.descending else asc(sort_column)
        products = list(
            (
                await self.session.execute(
                    select(Product)
                    .where(*predicates)
                    .order_by(ordering, Product.external_id.asc())
                    .offset(query.offset)
                    .limit(query.limit)
                )
            ).scalars()
        )
        if not products:
            return []
        trend_rows = (
            await self.session.execute(
                select(CategoryTrend)
                .where(
                    CategoryTrend.site == site_name,
                    CategoryTrend.category_external_id.in_(
                        {product.category_external_id for product in products}
                    ),
                )
                .order_by(CategoryTrend.date.desc())
            )
        ).scalars()
        latest: dict[str, CategoryTrend] = {}
        for trend in trend_rows:
            latest.setdefault(trend.category_external_id, trend)
        return [(product, latest.get(product.category_external_id)) for product in products]

    async def operational_signals(
        self, product_ids: list[UUID]
    ) -> dict[UUID, SelectionOperationalSignals]:
        """Aggregate deterministic product-level risk and factory signals."""
        if not product_ids:
            return {}

        logistics_rows = await self.session.execute(
            select(
                OrderItem.product_id,
                func.count(distinct(OrderItem.order_id)).label("order_count"),
                func.count(
                    distinct(
                        case(
                            (
                                LogisticsRecord.status.in_(RISKY_LOGISTICS_STATUSES),
                                OrderItem.order_id,
                            )
                        )
                    )
                ).label("risky_order_count"),
            )
            .join(LogisticsRecord, LogisticsRecord.order_id == OrderItem.order_id)
            .where(OrderItem.product_id.in_(product_ids))
            .group_by(OrderItem.product_id)
        )
        logistics_rates = {
            product_id: Decimal(risky_count) / Decimal(order_count)
            for product_id, order_count, risky_count in logistics_rows
            if order_count
        }

        after_sales_rows = await self.session.execute(
            select(
                OrderItem.product_id,
                func.count(distinct(OrderItem.id)).label("item_count"),
                func.count(
                    distinct(
                        case(
                            (
                                ReturnRefund.status != "rejected",
                                ReturnRefund.order_item_id,
                            )
                        )
                    )
                ).label("return_count"),
            )
            .outerjoin(ReturnRefund, ReturnRefund.order_item_id == OrderItem.id)
            .where(OrderItem.product_id.in_(product_ids))
            .group_by(OrderItem.product_id)
        )
        after_sales_rates = {
            product_id: Decimal(return_count) / Decimal(item_count)
            for product_id, item_count, return_count in after_sales_rows
            if item_count
        }

        factory_rows = await self.session.execute(
            select(
                Sku.product_id,
                func.count(distinct(Sku.id)).label("sku_count"),
                func.count(distinct(case((Sku.status.in_(ACTIVE_SKU_STATUSES), Sku.id)))).label(
                    "active_sku_count"
                ),
                func.count(
                    distinct(
                        case(
                            (
                                (InventoryRecord.available_stock >= InventoryRecord.safety_stock)
                                & (InventoryRecord.stock_status != "out_of_stock"),
                                Sku.id,
                            )
                        )
                    )
                ).label("ready_sku_count"),
            )
            .outerjoin(InventoryRecord, InventoryRecord.sku_id == Sku.id)
            .where(Sku.product_id.in_(product_ids))
            .group_by(Sku.product_id)
        )
        factory_scores = {
            product_id: (
                Decimal(active_count) / Decimal(sku_count)
                + Decimal(ready_count) / Decimal(sku_count)
            )
            / Decimal("2")
            for product_id, sku_count, active_count, ready_count in factory_rows
            if sku_count
        }

        return {
            product_id: SelectionOperationalSignals(
                logistics_risk_rate=logistics_rates.get(product_id),
                after_sales_rate=after_sales_rates.get(product_id),
                factory_fit_score=factory_scores.get(product_id),
            )
            for product_id in product_ids
        }

    @staticmethod
    def decimal(value: Decimal | None) -> Decimal | None:
        return Decimal(value) if value is not None else None
