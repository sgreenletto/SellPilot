from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from sellpilot.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SourceTrackedMixin:
    external_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(
        String(50), default="simulated_experiment", nullable=False
    )
    is_mock_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Shop(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shops"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="mock", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Product(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_shop_status_updated", "shop_id", "status", "updated_at"),
        Index("ix_products_site_category", "site", "category_external_id"),
        CheckConstraint("price >= 0", name="price_nonnegative"),
        CheckConstraint("cost >= 0", name="cost_nonnegative"),
        CheckConstraint("shipping_cost >= 0", name="shipping_cost_nonnegative"),
        CheckConstraint("rating >= 0 AND rating <= 5", name="rating_range"),
    )

    shop_id: Mapped[UUID] = mapped_column(
        ForeignKey("shops.id", ondelete="RESTRICT"), nullable=False
    )
    source_shop_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    category_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    site: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    sales_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False)
    favorite_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Sku(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skus"
    __table_args__ = (
        Index("ix_skus_product_status", "product_id", "status"),
        CheckConstraint("price >= 0", name="price_nonnegative"),
        CheckConstraint("cost >= 0", name="cost_nonnegative"),
        CheckConstraint("weight >= 0", name="weight_nonnegative"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    seller_sku: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    variation_name: Mapped[str] = mapped_column(String(100), nullable=False)
    variation_value: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InventoryRecord(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inventory_records"
    __table_args__ = (
        UniqueConstraint("sku_id", "warehouse_external_id", name="uq_inventory_sku_warehouse"),
        Index("ix_inventory_status_updated", "stock_status", "updated_at"),
        CheckConstraint("available_stock >= 0", name="available_nonnegative"),
        CheckConstraint("reserved_stock >= 0", name="reserved_nonnegative"),
        CheckConstraint("safety_stock >= 0", name="safety_nonnegative"),
    )

    sku_id: Mapped[UUID] = mapped_column(ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False)
    warehouse_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    warehouse_name: Mapped[str] = mapped_column(String(200), nullable=False)
    available_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_status: Mapped[str] = mapped_column(String(32), nullable=False)


class Order(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_shop_status_created", "shop_id", "order_status", "source_created_at"),
        Index("ix_orders_buyer_created", "buyer_external_id", "source_created_at"),
        CheckConstraint("subtotal >= 0", name="subtotal_nonnegative"),
        CheckConstraint("shipping_fee >= 0", name="shipping_fee_nonnegative"),
        CheckConstraint("discount_amount >= 0", name="discount_nonnegative"),
        CheckConstraint("total_amount >= 0", name="total_nonnegative"),
    )

    shop_id: Mapped[UUID] = mapped_column(
        ForeignKey("shops.id", ondelete="RESTRICT"), nullable=False
    )
    source_shop_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    buyer_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    site: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    order_status: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    source_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrderItem(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        Index("ix_order_items_order", "order_id"),
        Index("ix_order_items_product", "product_id"),
        Index("ix_order_items_sku", "sku_id"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_nonnegative"),
        CheckConstraint("subtotal >= 0", name="subtotal_nonnegative"),
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    sku_id: Mapped[UUID] = mapped_column(ForeignKey("skus.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)


class Review(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        Index("ix_reviews_product_created", "product_id", "source_created_at"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    sku_id: Mapped[UUID | None] = mapped_column(ForeignKey("skus.id", ondelete="RESTRICT"))
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"))
    buyer_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_zh: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    sentiment_hint: Mapped[str] = mapped_column(String(32), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LogisticsRecord(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "logistics_records"

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    tracking_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    carrier: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    origin: Mapped[str] = mapped_column(String(200), nullable=False)
    destination: Mapped[str] = mapped_column(String(200), nullable=False)
    estimated_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_location: Mapped[str | None] = mapped_column(String(200))


class LogisticsTrack(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "logistics_tracks"
    __table_args__ = (Index("ix_logistics_tracks_record_event", "logistics_id", "event_time"),)

    logistics_id: Mapped[UUID] = mapped_column(
        ForeignKey("logistics_records.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CustomerSession(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customer_sessions"
    __table_args__ = (Index("ix_customer_sessions_status_created", "status", "source_created_at"),)

    buyer_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"))
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    intent: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CustomerMessage(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customer_messages"
    __table_args__ = (Index("ix_customer_messages_session_time", "session_id", "message_time"),)

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("customer_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sender_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    message_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReturnRefund(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "returns_refunds"
    __table_args__ = (
        Index("ix_returns_refunds_order_status", "order_id", "status"),
        CheckConstraint("amount >= 0", name="amount_nonnegative"),
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    order_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False
    )
    buyer_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    request_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CategoryTrend(SourceTrackedMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "category_trends"
    __table_args__ = (
        UniqueConstraint(
            "site",
            "category_external_id",
            "date",
            name="uq_category_trends_site_category_date",
        ),
        CheckConstraint("search_index >= 0", name="search_nonnegative"),
        CheckConstraint("sales_index >= 0", name="sales_nonnegative"),
        CheckConstraint("competition_index >= 0", name="competition_nonnegative"),
        CheckConstraint("average_price >= 0", name="average_price_nonnegative"),
    )

    site: Mapped[str] = mapped_column(String(32), nullable=False)
    category_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    category_name: Mapped[str] = mapped_column(String(200), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    search_index: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    sales_index: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    competition_index: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    average_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    growth_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
