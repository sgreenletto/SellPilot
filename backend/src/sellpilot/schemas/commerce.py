from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ProductResponse(BaseModel):
    product_id: str
    title: str
    site: str
    category_id: str
    category_name: str
    currency: str
    price: Decimal
    cost: Decimal
    shipping_cost: Decimal
    sales_count: int
    rating: Decimal
    review_count: int
    status: str
    updated_at: datetime | None
    is_mock_data: bool


class OrderResponse(BaseModel):
    order_id: str
    buyer_id: str
    site: str
    currency: str
    order_status: str
    payment_status: str
    total_amount: Decimal
    created_at: datetime
    is_mock_data: bool


class LogisticsTrackResponse(BaseModel):
    track_id: str
    status: str
    location: str
    description: str
    event_time: datetime


class LogisticsResponse(BaseModel):
    logistics_id: str
    order_id: str
    tracking_number: str
    carrier: str
    status: str
    latest_location: str | None
    tracks: list[LogisticsTrackResponse]
    is_mock_data: bool


class MessageResponse(BaseModel):
    message_id: str
    sender_type: str
    content: str
    language: str
    message_time: datetime
    is_mock_data: bool


class InventoryResponse(BaseModel):
    inventory_id: str
    sku_id: str
    product_id: str
    warehouse_id: str
    available_stock: int
    reserved_stock: int
    safety_stock: int
    stock_status: str
    updated_at: datetime | None
    is_mock_data: bool


class ReturnRefundResponse(BaseModel):
    return_id: str
    order_id: str
    request_type: str
    reason_type: str
    amount: Decimal
    status: str
    requested_at: datetime
    completed_at: datetime | None
    is_mock_data: bool
