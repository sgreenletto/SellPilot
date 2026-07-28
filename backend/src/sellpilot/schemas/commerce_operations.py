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
