from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from sellpilot.core.enums import ToolRiskLevel
from sellpilot.core.exceptions import ParameterError, ResourceNotFoundError
from sellpilot.schemas.commerce import (
    InventoryResponse,
    LogisticsResponse,
    OrderResponse,
    ProductResponse,
)
from sellpilot.services.commerce_query import CommerceQueryService
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition, ToolExecutionContext
from sellpilot.tools.registry import ToolRegistry


class CommerceToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListProductsInput(CommerceToolModel):
    status: str | None = Field(default=None, max_length=32)
    site: str | None = Field(default=None, max_length=32)
    shop_id: str | None = Field(default=None, max_length=100)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class ListProductsOutput(CommerceToolModel):
    products: list[ProductResponse]
    count: int = Field(ge=0)
    is_mock_data: bool


class GetProductInput(CommerceToolModel):
    product_id: str = Field(min_length=1, max_length=100)


class ProductSkuSummary(CommerceToolModel):
    external_id: str
    seller_sku: str
    name: str
    variation_name: str
    variation_value: str


class ProductSpecification(CommerceToolModel):
    name: str
    value: str


class ProductDetail(ProductResponse):
    description: str
    skus: list[ProductSkuSummary] = Field(default_factory=list)
    specifications: list[ProductSpecification] = Field(default_factory=list)


class GetProductOutput(CommerceToolModel):
    product: ProductDetail


class ListProductSkusInput(CommerceToolModel):
    product_id: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=32)
    seller_sku: str | None = Field(default=None, max_length=100)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class SkuResponse(CommerceToolModel):
    sku_id: str
    product_id: str
    seller_sku: str
    variation_name: str
    variation_value: str
    price: Decimal
    cost: Decimal
    weight: Decimal
    status: str
    updated_at: datetime | None
    is_mock_data: bool


class ListProductSkusOutput(CommerceToolModel):
    skus: list[SkuResponse]
    count: int = Field(ge=0)
    is_mock_data: bool


class ListInventoryInput(CommerceToolModel):
    status: str | None = Field(default=None, max_length=32)
    shop_id: str | None = Field(default=None, max_length=100)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class ListInventoryOutput(CommerceToolModel):
    inventory: list[InventoryResponse]
    count: int = Field(ge=0)
    is_mock_data: bool


class ListLowStockInput(CommerceToolModel):
    shop_id: str | None = Field(default=None, max_length=100)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class ListOrdersInput(CommerceToolModel):
    status: str | None = Field(default=None, max_length=32)
    shop_id: str | None = Field(default=None, max_length=100)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class ListOrdersOutput(CommerceToolModel):
    orders: list[OrderResponse]
    count: int = Field(ge=0)
    is_mock_data: bool


class GetOrderInput(CommerceToolModel):
    order_id: str = Field(min_length=1, max_length=100)


class GetOrderOutput(CommerceToolModel):
    order: OrderResponse


class GetOrderLogisticsInput(CommerceToolModel):
    order_id: str = Field(min_length=1, max_length=100)


class GetOrderLogisticsOutput(CommerceToolModel):
    logistics: LogisticsResponse


def _service(context: ToolExecutionContext) -> CommerceQueryService:
    if context.session is None or context.settings is None:
        raise ParameterError("commerce tools require database session and settings")
    return CommerceQueryService(context.session, context.settings)


def _mock_marker(items: list[BaseModel]) -> bool:
    return all(bool(getattr(item, "is_mock_data", False)) for item in items)


async def _list_products(payload: ListProductsInput, context: ToolExecutionContext):
    rows = await _service(context).list_products(**payload.model_dump())
    products = [ProductResponse.model_validate(row) for row in rows]
    return ListProductsOutput(
        products=products,
        count=len(products),
        is_mock_data=_mock_marker(products),
    )


async def _get_product(payload: GetProductInput, context: ToolExecutionContext):
    row = await _service(context).get_product(payload.product_id)
    if not row:
        raise ResourceNotFoundError("Product not found")
    return GetProductOutput(product=ProductDetail.model_validate(row))


async def _list_product_skus(
    payload: ListProductSkusInput,
    context: ToolExecutionContext,
):
    rows = await _service(context).list_skus(**payload.model_dump())
    skus = [SkuResponse.model_validate(row) for row in rows]
    return ListProductSkusOutput(
        skus=skus,
        count=len(skus),
        is_mock_data=_mock_marker(skus),
    )


async def _list_inventory(payload: ListInventoryInput, context: ToolExecutionContext):
    rows = await _service(context).list_inventory(**payload.model_dump())
    inventory = [InventoryResponse.model_validate(row) for row in rows]
    return ListInventoryOutput(
        inventory=inventory,
        count=len(inventory),
        is_mock_data=_mock_marker(inventory),
    )


async def _list_low_stock(payload: ListLowStockInput, context: ToolExecutionContext):
    rows = await _service(context).list_inventory(
        status="low_stock",
        **payload.model_dump(),
    )
    inventory = [InventoryResponse.model_validate(row) for row in rows]
    return ListInventoryOutput(
        inventory=inventory,
        count=len(inventory),
        is_mock_data=_mock_marker(inventory),
    )


async def _list_orders(payload: ListOrdersInput, context: ToolExecutionContext):
    rows = await _service(context).list_orders(**payload.model_dump())
    orders = [OrderResponse.model_validate(row) for row in rows]
    return ListOrdersOutput(
        orders=orders,
        count=len(orders),
        is_mock_data=_mock_marker(orders),
    )


async def _get_order(payload: GetOrderInput, context: ToolExecutionContext):
    row = await _service(context).get_order(payload.order_id)
    if not row:
        raise ResourceNotFoundError("Order not found")
    return GetOrderOutput(order=OrderResponse.model_validate(row))


async def _get_order_logistics(
    payload: GetOrderLogisticsInput,
    context: ToolExecutionContext,
):
    row = await _service(context).get_logistics(payload.order_id)
    if not row:
        raise ResourceNotFoundError("Logistics record not found")
    return GetOrderLogisticsOutput(logistics=LogisticsResponse.model_validate(row))


def build_commerce_read_tools() -> tuple[ToolDefinition, ...]:
    retry = RetryPolicy(
        max_attempts=1,
        initial_delay_ms=0,
        max_delay_ms=0,
        backoff_multiplier=1,
    )
    shared = {
        "version": "1.0.0",
        "risk_level": ToolRiskLevel.READ,
        "retry_policy": retry,
        "idempotent": True,
        "expose_to_mcp": False,
        "enabled": True,
    }
    return (
        ToolDefinition(
            name="list_products",
            description="List bounded products through CommerceQueryService.",
            input_schema=ListProductsInput,
            output_schema=ListProductsOutput,
            timeout_seconds=10,
            handler=_list_products,
            **shared,
        ),
        ToolDefinition(
            name="get_product",
            description="Read one product and its SKU summaries through CommerceQueryService.",
            input_schema=GetProductInput,
            output_schema=GetProductOutput,
            timeout_seconds=10,
            handler=_get_product,
            **shared,
        ),
        ToolDefinition(
            name="list_product_skus",
            description="List bounded SKU records through CommerceQueryService.",
            input_schema=ListProductSkusInput,
            output_schema=ListProductSkusOutput,
            timeout_seconds=10,
            handler=_list_product_skus,
            **shared,
        ),
        ToolDefinition(
            name="list_inventory",
            description="List bounded inventory records through CommerceQueryService.",
            input_schema=ListInventoryInput,
            output_schema=ListInventoryOutput,
            timeout_seconds=10,
            handler=_list_inventory,
            **shared,
        ),
        ToolDefinition(
            name="list_low_stock",
            description="List bounded low-stock inventory through CommerceQueryService.",
            input_schema=ListLowStockInput,
            output_schema=ListInventoryOutput,
            timeout_seconds=10,
            handler=_list_low_stock,
            **shared,
        ),
        ToolDefinition(
            name="list_orders",
            description="List bounded orders through CommerceQueryService.",
            input_schema=ListOrdersInput,
            output_schema=ListOrdersOutput,
            timeout_seconds=10,
            handler=_list_orders,
            **shared,
        ),
        ToolDefinition(
            name="get_order",
            description="Read one order through CommerceQueryService.",
            input_schema=GetOrderInput,
            output_schema=GetOrderOutput,
            timeout_seconds=10,
            handler=_get_order,
            **shared,
        ),
        ToolDefinition(
            name="get_order_logistics",
            description="Read order logistics and tracks through CommerceQueryService.",
            input_schema=GetOrderLogisticsInput,
            output_schema=GetOrderLogisticsOutput,
            timeout_seconds=10,
            handler=_get_order_logistics,
            **shared,
        ),
    )


def register_commerce_read_tools(registry: ToolRegistry) -> None:
    for definition in build_commerce_read_tools():
        registry.register(definition)
