import csv
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.commerce import (
    CategoryTrend,
    CustomerMessage,
    CustomerSession,
    InventoryRecord,
    LogisticsRecord,
    LogisticsTrack,
    Order,
    OrderItem,
    Product,
    ReturnRefund,
    Review,
    Shop,
    Sku,
)
from sellpilot.repositories.commerce_import import CommerceImportRepository
from sellpilot.schemas.commerce_import import (
    CategoryTrendCsvRow,
    CommerceImportResult,
    CustomerMessageCsvRow,
    CustomerSessionCsvRow,
    InventoryCsvRow,
    LogisticsCsvRow,
    LogisticsTrackCsvRow,
    OrderCsvRow,
    OrderItemCsvRow,
    ProductCsvRow,
    ReturnRefundCsvRow,
    ReviewCsvRow,
    SkuCsvRow,
)

RowT = TypeVar("RowT", bound=BaseModel)

FILE_SCHEMAS: dict[str, type[BaseModel]] = {
    "products.csv": ProductCsvRow,
    "skus.csv": SkuCsvRow,
    "inventory.csv": InventoryCsvRow,
    "orders.csv": OrderCsvRow,
    "order_items.csv": OrderItemCsvRow,
    "reviews.csv": ReviewCsvRow,
    "logistics.csv": LogisticsCsvRow,
    "logistics_tracks.csv": LogisticsTrackCsvRow,
    "customer_sessions.csv": CustomerSessionCsvRow,
    "customer_messages.csv": CustomerMessageCsvRow,
    "returns_refunds.csv": ReturnRefundCsvRow,
    "category_trends.csv": CategoryTrendCsvRow,
}


class CommerceImportError(ValueError):
    pass


class CommerceImportService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = CommerceImportRepository(session)

    @staticmethod
    def _read_rows(data_dir: Path, filename: str, schema: type[RowT]) -> list[RowT]:
        path = data_dir / filename
        if not path.is_file():
            raise CommerceImportError(f"missing required data file: {filename}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            raw_rows = list(csv.DictReader(handle))
        try:
            return [schema.model_validate(row) for row in raw_rows]
        except ValidationError as exc:
            raise CommerceImportError(f"{filename} failed schema validation: {exc}") from exc

    def validate_package(self, data_dir: Path) -> dict[str, list[BaseModel]]:
        if not data_dir.is_dir():
            raise CommerceImportError(f"data directory does not exist: {data_dir}")
        return {
            filename: self._read_rows(data_dir, filename, schema)
            for filename, schema in FILE_SCHEMAS.items()
        }

    async def _insert_missing(
        self,
        model: type[Any],
        records: list[Any],
        key: str,
    ) -> tuple[int, int]:
        existing = await self.repository.id_map(model)
        missing = [record for record in records if getattr(record, key) not in existing]
        self.repository.add_all(missing)
        await self.repository.flush()
        return len(missing), len(records) - len(missing)

    async def import_package(self, data_dir: Path) -> CommerceImportResult:
        rows = self.validate_package(data_dir)
        inserted: dict[str, int] = {}
        skipped: dict[str, int] = {}

        products_csv = rows["products.csv"]
        orders_csv = rows["orders.csv"]
        shop_records = [
            Shop(
                external_id="SELLPILOT_MOCK_SHOP",
                name="SellPilot Mock Shop",
                platform="Shopee",
                mode="mock",
                source_type="simulated_experiment",
                is_mock_data=True,
                is_active=True,
            )
        ]
        inserted["shops"], skipped["shops"] = await self._insert_missing(
            Shop, shop_records, "external_id"
        )
        shop_map = await self.repository.id_map(Shop)
        logical_shop_id = shop_map["SELLPILOT_MOCK_SHOP"]

        product_records = [
            Product(
                external_id=row.product_id,
                shop_id=logical_shop_id,
                source_shop_external_id=row.shop_id,
                title=row.title,
                category_external_id=row.category_id,
                category_name=row.category_name,
                description=row.description,
                platform=row.platform,
                site=row.site,
                source_type=row.source_type,
                currency=row.currency,
                price=row.price,
                cost=row.cost,
                shipping_cost=row.shipping_cost,
                sales_count=row.sales_count,
                rating=row.rating,
                review_count=row.review_count,
                favorite_count=row.favorite_count,
                status=row.status,
                source_created_at=row.created_at,
                source_updated_at=row.updated_at,
                collected_at=row.collected_at,
                is_mock_data=row.is_mock_data,
            )
            for row in products_csv
        ]
        inserted["products"], skipped["products"] = await self._insert_missing(
            Product, product_records, "external_id"
        )
        product_map = await self.repository.id_map(Product)

        sku_records = [
            Sku(
                external_id=row.sku_id,
                product_id=product_map[row.product_id],
                seller_sku=row.seller_sku,
                variation_name=row.variation_name,
                variation_value=row.variation_value,
                price=row.price,
                cost=row.cost,
                weight=row.weight,
                status=row.status,
                source_created_at=row.created_at,
                source_type="simulated_experiment",
                is_mock_data=row.is_mock_data,
            )
            for row in rows["skus.csv"]
        ]
        inserted["skus"], skipped["skus"] = await self._insert_missing(
            Sku, sku_records, "external_id"
        )
        sku_map = await self.repository.id_map(Sku)

        inventory_records = [
            InventoryRecord(
                external_id=row.inventory_id,
                sku_id=sku_map[row.sku_id],
                warehouse_external_id=row.warehouse_id,
                warehouse_name=row.warehouse_name,
                available_stock=row.available_stock,
                reserved_stock=row.reserved_stock,
                safety_stock=row.safety_stock,
                stock_status=row.stock_status,
                source_updated_at=row.updated_at,
                source_type="simulated_experiment",
                is_mock_data=row.is_mock_data,
            )
            for row in rows["inventory.csv"]
        ]
        inserted["inventory_records"], skipped["inventory_records"] = await self._insert_missing(
            InventoryRecord, inventory_records, "external_id"
        )

        order_records = [
            Order(
                external_id=row.order_id,
                shop_id=logical_shop_id,
                source_shop_external_id=row.shop_id,
                buyer_external_id=row.buyer_id,
                site=row.site,
                currency=row.currency,
                order_status=row.order_status,
                payment_status=row.payment_status,
                subtotal=row.subtotal,
                shipping_fee=row.shipping_fee,
                discount_amount=row.discount_amount,
                total_amount=row.total_amount,
                source_created_at=row.created_at,
                paid_at=row.paid_at,
                shipped_at=row.shipped_at,
                completed_at=row.completed_at,
                cancelled_at=row.cancelled_at,
                source_type="simulated_experiment",
                is_mock_data=row.is_mock_data,
            )
            for row in orders_csv
        ]
        inserted["orders"], skipped["orders"] = await self._insert_missing(
            Order, order_records, "external_id"
        )
        order_map = await self.repository.id_map(Order)

        order_item_records = [
            OrderItem(
                external_id=row.order_item_id,
                order_id=order_map[row.order_id],
                product_id=product_map[row.product_id],
                sku_id=sku_map[row.sku_id],
                quantity=row.quantity,
                unit_price=row.unit_price,
                subtotal=row.subtotal,
                source_type="simulated_experiment",
                is_mock_data=row.is_mock_data,
            )
            for row in rows["order_items.csv"]
        ]
        inserted["order_items"], skipped["order_items"] = await self._insert_missing(
            OrderItem, order_item_records, "external_id"
        )
        order_item_map = await self.repository.id_map(OrderItem)

        review_records = [
            Review(
                external_id=row.review_id,
                product_id=product_map[row.product_id],
                sku_id=sku_map.get(row.sku_id) if row.sku_id else None,
                order_id=order_map.get(row.order_id) if row.order_id else None,
                buyer_external_id=row.buyer_id,
                rating=row.rating,
                content=row.content,
                content_zh=row.content_zh,
                language=row.language,
                sentiment_hint=row.sentiment_hint,
                issue_type=row.issue_type,
                source_created_at=row.created_at,
                source_type="simulated_experiment",
                is_mock_data=row.is_mock_data,
            )
            for row in rows["reviews.csv"]
        ]
        inserted["reviews"], skipped["reviews"] = await self._insert_missing(
            Review, review_records, "external_id"
        )

        logistics_records = [
            LogisticsRecord(
                external_id=row.logistics_id,
                order_id=order_map[row.order_id],
                tracking_number=row.tracking_number,
                carrier=row.carrier,
                status=row.logistics_status,
                origin=row.origin,
                destination=row.destination,
                estimated_delivery_at=row.estimated_delivery_at,
                latest_location=row.latest_location,
                source_updated_at=row.updated_at,
                source_type="simulated_experiment",
                is_mock_data=row.is_mock_data,
            )
            for row in rows["logistics.csv"]
        ]
        inserted["logistics_records"], skipped["logistics_records"] = await self._insert_missing(
            LogisticsRecord, logistics_records, "external_id"
        )
        logistics_map = await self.repository.id_map(LogisticsRecord)
        tracking_map = {
            record.tracking_number: logistics_map[record.external_id]
            for record in logistics_records
        }

        track_records = [
            LogisticsTrack(
                external_id=row.track_id,
                logistics_id=tracking_map[row.tracking_number],
                status=row.status,
                location=row.location,
                description=row.description,
                event_time=row.event_time,
                source_type="simulated_experiment",
                is_mock_data=row.is_mock_data,
            )
            for row in rows["logistics_tracks.csv"]
        ]
        inserted["logistics_tracks"], skipped["logistics_tracks"] = await self._insert_missing(
            LogisticsTrack, track_records, "external_id"
        )

        session_records = [
            CustomerSession(
                external_id=row.session_id,
                buyer_external_id=row.buyer_id,
                order_id=order_map.get(row.order_id) if row.order_id else None,
                product_id=product_map.get(row.product_id) if row.product_id else None,
                language=row.language,
                intent=row.intent,
                risk_level=row.risk_level,
                status=row.session_status,
                source_created_at=row.created_at,
                source_type="simulated_experiment",
                is_mock_data=row.is_mock_data,
            )
            for row in rows["customer_sessions.csv"]
        ]
        inserted["customer_sessions"], skipped["customer_sessions"] = await self._insert_missing(
            CustomerSession, session_records, "external_id"
        )
        session_map = await self.repository.id_map(CustomerSession)

        message_records = [
            CustomerMessage(
                external_id=row.message_id,
                session_id=session_map[row.session_id],
                sender_type=row.sender_type,
                content=row.content,
                language=row.language,
                message_time=row.message_time,
                source_type="simulated_experiment",
                is_mock_data=row.is_mock_data,
            )
            for row in rows["customer_messages.csv"]
        ]
        inserted["customer_messages"], skipped["customer_messages"] = await self._insert_missing(
            CustomerMessage, message_records, "external_id"
        )

        return_records = [
            ReturnRefund(
                external_id=row.return_id,
                order_id=order_map[row.order_id],
                order_item_id=order_item_map[row.order_item_id],
                buyer_external_id=row.buyer_id,
                request_type=row.request_type,
                reason_type=row.reason_type,
                reason_description=row.reason_description,
                amount=row.amount,
                status=row.status,
                requested_at=row.requested_at,
                completed_at=row.completed_at,
                source_type="simulated_experiment",
                is_mock_data=row.is_mock_data,
            )
            for row in rows["returns_refunds.csv"]
        ]
        inserted["returns_refunds"], skipped["returns_refunds"] = await self._insert_missing(
            ReturnRefund, return_records, "external_id"
        )

        trend_records = [
            CategoryTrend(
                external_id=row.trend_id,
                site=row.site,
                category_external_id=row.category_id,
                category_name=row.category_name,
                date=row.date,
                search_index=row.search_index,
                sales_index=row.sales_index,
                competition_index=row.competition_index,
                average_price=row.average_price,
                growth_rate=row.growth_rate,
                source_type="simulated_experiment",
                is_mock_data=row.is_mock_data,
            )
            for row in rows["category_trends.csv"]
        ]
        inserted["category_trends"], skipped["category_trends"] = await self._insert_missing(
            CategoryTrend, trend_records, "external_id"
        )

        return CommerceImportResult(
            files=len(FILE_SCHEMAS),
            rows_validated=sum(len(file_rows) for file_rows in rows.values()),
            inserted=inserted,
            skipped=skipped,
        )
