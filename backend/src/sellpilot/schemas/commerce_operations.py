from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OperationRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=255)


class PriceUpdateRequest(OperationRequest):
    sku_id: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(gt=0)


class InventoryUpdateRequest(OperationRequest):
    sku_id: str = Field(min_length=1, max_length=100)
    available_stock: int = Field(ge=0)


class ProductDraftPayload(BaseModel):
    product_id: str | None = Field(default=None, max_length=100)
    source_shop_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    category_id: str = Field(min_length=1, max_length=100)
    category_name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    site: str = Field(min_length=1, max_length=32)
    currency: str = Field(min_length=3, max_length=3)
    price: Decimal = Field(ge=0)
    cost: Decimal = Field(default=Decimal("0"), ge=0)
    shipping_cost: Decimal = Field(default=Decimal("0"), ge=0)
    source_type: str = Field(default="manual_import", min_length=1, max_length=50)


class ProductDraftRequest(OperationRequest):
    product: ProductDraftPayload


class ProductImportRequest(OperationRequest):
    products: list[ProductDraftPayload] = Field(min_length=1, max_length=500)


class CandidateRequest(OperationRequest):
    title: str = Field(min_length=1, max_length=500)
    source_type: str = Field(default="simulated_experiment", max_length=50)
    is_mock_data: bool = True


class CandidateResponse(BaseModel):
    product_id: str
    title: str
    source_type: str
    is_mock_data: bool
    created_at: datetime
