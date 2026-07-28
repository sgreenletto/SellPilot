from datetime import UTC, datetime
from typing import Any, Never
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.adapters.base import PlatformAdapter
from sellpilot.core.exceptions import PlatformFeatureNotImplementedError
from sellpilot.db.models.commerce import (
    CustomerMessage,
    InventoryRecord,
    LogisticsRecord,
    LogisticsTrack,
    Order,
    Product,
    Review,
    Shop,
    Sku,
)
from sellpilot.schemas.platform import PlatformPingResult


class MockShopeeAdapter(PlatformAdapter):
    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    def _session(self) -> AsyncSession:
        if self.session is None:
            self._not_implemented("database_session")
        return self.session

    async def ping(self) -> PlatformPingResult:
        return PlatformPingResult(
            adapter="mock",
            configured=True,
            reachable=True,
            message="Mock adapter foundation is available",
        )

    async def get_capabilities(self) -> list[str]:
        return [
            "system.ping",
            "platform.contracts",
            "products.read",
            "products.create_draft",
            "products.update_draft",
            "orders.read",
            "logistics.read",
            "reviews.read",
            "messages.read",
        ]

    def _not_implemented(self, feature: str) -> Never:
        raise PlatformFeatureNotImplementedError(
            f"Mock Shopee business feature '{feature}' is not implemented in the foundation phase"
        )

    async def list_products(self, **filters: Any) -> list[dict[str, Any]]:
        statement = select(Product).order_by(Product.updated_at.desc())
        if status := filters.get("status"):
            statement = statement.where(Product.status == status)
        if site := filters.get("site"):
            statement = statement.where(Product.site == site)
        if shop_id := filters.get("shop_id"):
            statement = statement.where(Product.source_shop_external_id == shop_id)
        statement = statement.offset(int(filters.get("offset", 0))).limit(
            min(int(filters.get("limit", 20)), 100)
        )
        records = (await self._session().execute(statement)).scalars().all()
        return [self._product(record) for record in records]

    async def get_product(self, product_id: str) -> dict[str, Any]:
        record = await self._session().scalar(
            select(Product).where(Product.external_id == product_id)
        )
        return self._product(record) if record else {}

    async def create_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        shop = await self._session().scalar(
            select(Shop).where(Shop.external_id == payload["source_shop_id"])
        )
        if shop is None:
            shop = await self._session().scalar(
                select(Shop)
                .join(Product, Product.shop_id == Shop.id)
                .where(Product.source_shop_external_id == payload["source_shop_id"])
            )
        if shop is None:
            return {}
        now = datetime.now(UTC)
        record = Product(
            external_id=payload.get("product_id") or f"DRAFT-{uuid4().hex[:16].upper()}",
            shop_id=shop.id,
            source_shop_external_id=shop.external_id,
            title=payload["title"],
            category_external_id=payload["category_id"],
            category_name=payload["category_name"],
            description=payload.get("description", ""),
            platform="shopee",
            site=payload["site"],
            currency=payload["currency"],
            price=payload["price"],
            cost=payload.get("cost", 0),
            shipping_cost=payload.get("shipping_cost", 0),
            sales_count=0,
            rating=0,
            review_count=0,
            favorite_count=0,
            status="draft",
            source_type=payload.get("source_type", "manual_import"),
            is_mock_data=True,
            source_created_at=now,
            collected_at=now,
            source_updated_at=now,
        )
        self._session().add(record)
        await self._session().flush()
        return self._product(record)

    async def update_product(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = await self._session().scalar(
            select(Product).where(Product.external_id == product_id)
        )
        if record is None:
            return {}
        mapping = {
            "title": "title",
            "category_id": "category_external_id",
            "category_name": "category_name",
            "description": "description",
            "site": "site",
            "currency": "currency",
            "price": "price",
            "cost": "cost",
            "shipping_cost": "shipping_cost",
        }
        for source, target in mapping.items():
            if source in payload:
                setattr(record, target, payload[source])
        record.status = "draft"
        record.source_updated_at = datetime.now(UTC)
        await self._session().flush()
        return self._product(record)

    async def publish_product(self, product_id: str) -> dict[str, Any]:
        record = await self._session().scalar(
            select(Product).where(Product.external_id == product_id)
        )
        if record is None:
            return {}
        record.status = "active"
        await self._session().flush()
        return self._product(record)

    async def unpublish_product(self, product_id: str) -> dict[str, Any]:
        record = await self._session().scalar(
            select(Product).where(Product.external_id == product_id)
        )
        if record is None:
            return {}
        record.status = "inactive"
        await self._session().flush()
        return self._product(record)

    async def update_price(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = await self._session().scalar(
            select(Sku).where(
                Sku.external_id == payload["sku_id"],
                Sku.product_id
                == select(Product.id).where(Product.external_id == product_id).scalar_subquery(),
            )
        )
        if record is None:
            return {}
        record.price = payload["price"]
        await self._session().flush()
        return {
            "product_id": product_id,
            "sku_id": record.external_id,
            "price": record.price,
            "is_mock_data": record.is_mock_data,
        }

    async def update_inventory(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = await self._session().scalar(
            select(InventoryRecord)
            .join(Sku)
            .join(Product)
            .where(
                Product.external_id == product_id,
                Sku.external_id == payload["sku_id"],
            )
        )
        if record is None:
            return {}
        record.available_stock = payload["available_stock"]
        if record.available_stock == 0:
            record.stock_status = "out_of_stock"
        elif record.available_stock <= record.safety_stock:
            record.stock_status = "low_stock"
        else:
            record.stock_status = "sufficient"
        await self._session().flush()
        return {
            "product_id": product_id,
            "sku_id": payload["sku_id"],
            "available_stock": record.available_stock,
            "stock_status": record.stock_status,
            "is_mock_data": record.is_mock_data,
        }

    async def list_orders(self, **filters: Any) -> list[dict[str, Any]]:
        statement = select(Order).order_by(Order.source_created_at.desc())
        if status := filters.get("status"):
            statement = statement.where(Order.order_status == status)
        if shop_id := filters.get("shop_id"):
            statement = statement.where(Order.source_shop_external_id == shop_id)
        statement = statement.offset(int(filters.get("offset", 0))).limit(
            min(int(filters.get("limit", 20)), 100)
        )
        records = (await self._session().execute(statement)).scalars().all()
        return [self._order(record) for record in records]

    async def get_order(self, order_id: str) -> dict[str, Any]:
        record = await self._session().scalar(select(Order).where(Order.external_id == order_id))
        return self._order(record) if record else {}

    async def get_logistics(self, order_id: str) -> dict[str, Any]:
        record = await self._session().scalar(
            select(LogisticsRecord)
            .join(Order, LogisticsRecord.order_id == Order.id)
            .where(Order.external_id == order_id)
        )
        if record is None:
            return {}
        tracks = (
            (
                await self._session().execute(
                    select(LogisticsTrack)
                    .where(LogisticsTrack.logistics_id == record.id)
                    .order_by(LogisticsTrack.event_time)
                )
            )
            .scalars()
            .all()
        )
        return {
            "logistics_id": record.external_id,
            "order_id": order_id,
            "tracking_number": record.tracking_number,
            "carrier": record.carrier,
            "status": record.status,
            "latest_location": record.latest_location,
            "tracks": [
                {
                    "track_id": track.external_id,
                    "status": track.status,
                    "location": track.location,
                    "description": track.description,
                    "event_time": track.event_time,
                }
                for track in tracks
            ],
            "is_mock_data": record.is_mock_data,
        }

    async def list_messages(self, **filters: Any) -> list[dict[str, Any]]:
        statement = select(CustomerMessage).order_by(CustomerMessage.message_time)
        if session_id := filters.get("session_id"):
            from sellpilot.db.models.commerce import CustomerSession

            statement = statement.join(CustomerSession).where(
                CustomerSession.external_id == session_id
            )
        statement = statement.limit(min(int(filters.get("limit", 100)), 200))
        records = (await self._session().execute(statement)).scalars().all()
        return [
            {
                "message_id": record.external_id,
                "sender_type": record.sender_type,
                "content": record.content,
                "language": record.language,
                "message_time": record.message_time,
                "is_mock_data": record.is_mock_data,
            }
            for record in records
        ]

    async def list_reviews(self, **filters: Any) -> list[dict[str, Any]]:
        statement = (
            select(Review, Product.external_id, Product.site)
            .join(Product, Review.product_id == Product.id)
            .order_by(Review.source_created_at.desc(), Review.external_id.asc())
        )
        if product_id := filters.get("product_id"):
            statement = statement.where(Product.external_id == product_id)
        if site := filters.get("site"):
            statement = statement.where(Product.site == site)
        if language := filters.get("language"):
            statement = statement.where(Review.language == language)
        if languages := filters.get("languages"):
            statement = statement.where(Review.language.in_(languages))
        if min_rating := filters.get("min_rating"):
            statement = statement.where(Review.rating >= int(min_rating))
        if max_rating := filters.get("max_rating"):
            statement = statement.where(Review.rating <= int(max_rating))
        if created_from := filters.get("created_from"):
            statement = statement.where(Review.source_created_at >= created_from)
        if created_to := filters.get("created_to"):
            statement = statement.where(Review.source_created_at <= created_to)
        offset = max(int(filters.get("offset", 0)), 0)
        limit = min(max(int(filters.get("limit", 20)), 1), 100)
        rows = (await self._session().execute(statement.offset(offset).limit(limit))).all()
        return [
            {
                "review_id": record.external_id,
                "product_id": product_id,
                "site": site,
                "rating": record.rating,
                "content": record.content,
                "translated_content": record.content_zh,
                "language": record.language,
                "sentiment_hint": record.sentiment_hint,
                "issue_type": record.issue_type,
                "created_at": record.source_created_at,
                "source_type": record.source_type,
                "is_mock_data": record.is_mock_data,
            }
            for record, product_id, site in rows
        ]

    async def send_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._not_implemented("send_message")

    @staticmethod
    def _product(record: Product) -> dict[str, Any]:
        return {
            "product_id": record.external_id,
            "title": record.title,
            "site": record.site,
            "category_id": record.category_external_id,
            "category_name": record.category_name,
            "currency": record.currency,
            "price": record.price,
            "cost": record.cost,
            "shipping_cost": record.shipping_cost,
            "sales_count": record.sales_count,
            "rating": record.rating,
            "review_count": record.review_count,
            "status": record.status,
            "updated_at": record.source_updated_at,
            "is_mock_data": record.is_mock_data,
        }

    @staticmethod
    def _order(record: Order) -> dict[str, Any]:
        return {
            "order_id": record.external_id,
            "buyer_id": record.buyer_external_id,
            "site": record.site,
            "currency": record.currency,
            "order_status": record.order_status,
            "payment_status": record.payment_status,
            "total_amount": record.total_amount,
            "created_at": record.source_created_at,
            "is_mock_data": record.is_mock_data,
        }
