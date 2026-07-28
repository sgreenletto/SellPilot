from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CsvRow(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    is_mock_data: bool

    @field_validator("*", mode="before")
    @classmethod
    def empty_string_as_none(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def require_mock_data(self) -> "CsvRow":
        if not self.is_mock_data:
            raise ValueError("only rows with is_mock_data=true may be imported")
        return self


class ProductCsvRow(CsvRow):
    product_id: str
    shop_id: str
    shop_name: str
    title: str
    category_id: str
    category_name: str
    description: str
    platform: str
    site: str
    source_type: str
    currency: str
    price: Decimal = Field(ge=0)
    cost: Decimal = Field(ge=0)
    shipping_cost: Decimal = Field(ge=0)
    sales_count: int = Field(ge=0)
    rating: Decimal = Field(ge=0, le=5)
    review_count: int = Field(ge=0)
    favorite_count: int = Field(ge=0)
    status: str
    created_at: datetime
    updated_at: datetime
    collected_at: datetime


class SkuCsvRow(CsvRow):
    sku_id: str
    product_id: str
    seller_sku: str
    variation_name: str
    variation_value: str
    price: Decimal = Field(ge=0)
    cost: Decimal = Field(ge=0)
    weight: Decimal = Field(ge=0)
    status: str
    created_at: datetime


class InventoryCsvRow(CsvRow):
    inventory_id: str
    sku_id: str
    warehouse_id: str
    warehouse_name: str
    available_stock: int = Field(ge=0)
    reserved_stock: int = Field(ge=0)
    safety_stock: int = Field(ge=0)
    stock_status: str
    updated_at: datetime


class OrderCsvRow(CsvRow):
    order_id: str
    shop_id: str
    buyer_id: str
    site: str
    currency: str
    order_status: str
    payment_status: str
    subtotal: Decimal = Field(ge=0)
    shipping_fee: Decimal = Field(ge=0)
    discount_amount: Decimal = Field(ge=0)
    total_amount: Decimal = Field(ge=0)
    created_at: datetime
    paid_at: datetime | None = None
    shipped_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None

    @model_validator(mode="after")
    def reconcile_total(self) -> "OrderCsvRow":
        if self.total_amount != self.subtotal + self.shipping_fee - self.discount_amount:
            raise ValueError("order total does not reconcile")
        return self


class OrderItemCsvRow(CsvRow):
    order_item_id: str
    order_id: str
    product_id: str
    sku_id: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    subtotal: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def reconcile_subtotal(self) -> "OrderItemCsvRow":
        if self.subtotal != self.unit_price * self.quantity:
            raise ValueError("order item subtotal does not reconcile")
        return self


class ReviewCsvRow(CsvRow):
    review_id: str
    product_id: str
    sku_id: str | None = None
    order_id: str | None = None
    buyer_id: str
    rating: int = Field(ge=1, le=5)
    content: str
    content_zh: str | None = None
    language: str
    sentiment_hint: str
    issue_type: str
    created_at: datetime


class LogisticsCsvRow(CsvRow):
    logistics_id: str
    order_id: str
    tracking_number: str
    carrier: str
    logistics_status: str
    origin: str
    destination: str
    estimated_delivery_at: datetime | None = None
    latest_location: str | None = None
    updated_at: datetime


class LogisticsTrackCsvRow(CsvRow):
    track_id: str
    tracking_number: str
    status: str
    location: str
    description: str
    event_time: datetime


class CustomerSessionCsvRow(CsvRow):
    session_id: str
    buyer_id: str
    order_id: str | None = None
    product_id: str | None = None
    language: str
    intent: str
    risk_level: str
    session_status: str
    created_at: datetime


class CustomerMessageCsvRow(CsvRow):
    message_id: str
    session_id: str
    sender_type: str
    content: str
    language: str
    message_time: datetime


class ReturnRefundCsvRow(CsvRow):
    return_id: str
    order_id: str
    order_item_id: str
    buyer_id: str
    request_type: str
    reason_type: str
    reason_description: str
    amount: Decimal = Field(ge=0)
    status: str
    requested_at: datetime
    completed_at: datetime | None = None


class CategoryTrendCsvRow(CsvRow):
    trend_id: str
    site: str
    category_id: str
    category_name: str
    date: date
    search_index: Decimal = Field(ge=0)
    sales_index: Decimal = Field(ge=0)
    competition_index: Decimal = Field(ge=0)
    average_price: Decimal = Field(ge=0)
    growth_rate: Decimal


class CommerceImportResult(BaseModel):
    files: int
    rows_validated: int
    inserted: dict[str, int]
    skipped: dict[str, int]

    @property
    def inserted_total(self) -> int:
        return sum(self.inserted.values())

    @property
    def skipped_total(self) -> int:
        return sum(self.skipped.values())
