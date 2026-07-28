from decimal import Decimal

from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.commerce import CategoryTrend, Product
from sellpilot.schemas.selection import SelectionCandidateQuery

SITE_NAMES = {
    "sg": "Singapore",
    "my": "Malaysia",
    "ph": "Philippines",
    "th": "Thailand",
    "vn": "Vietnam",
    "id": "Indonesia",
}


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

    @staticmethod
    def decimal(value: Decimal | None) -> Decimal | None:
        return Decimal(value) if value is not None else None
