from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ReplenishmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReplenishmentAnalysisRequest(ReplenishmentModel):
    shop_external_id: str = Field(min_length=1, max_length=100)
    analysis_days: int = Field(default=30, ge=1, le=365)
    lead_time_days: int = Field(default=14, ge=1, le=180)
    safety_factor: Decimal = Field(default=Decimal("1.20"), ge=Decimal("1"), le=Decimal("3"))
    only_replenishment: bool = True


class ReplenishmentRecommendation(ReplenishmentModel):
    product_id: str
    product_title: str
    sku_id: str
    seller_sku: str
    site: str
    available_stock: int = Field(ge=0)
    safety_stock: int = Field(ge=0)
    units_sold: int = Field(ge=0)
    average_daily_sales: Decimal = Field(ge=0)
    days_of_supply: Decimal | None = Field(default=None, ge=0)
    target_stock: int = Field(ge=0)
    recommended_quantity: int = Field(ge=0)
    risk_level: str
    reason: str
    is_mock_data: bool


class ReplenishmentSummary(ReplenishmentModel):
    analyzed_skus: int = Field(ge=0)
    replenishment_skus: int = Field(ge=0)
    critical_skus: int = Field(ge=0)
    recommended_units: int = Field(ge=0)


class ReplenishmentAnalysisOutput(ReplenishmentModel):
    shop_external_id: str
    analysis_days: int
    lead_time_days: int
    safety_factor: Decimal
    formula_version: str
    summary: ReplenishmentSummary
    recommendations: list[ReplenishmentRecommendation]
    is_mock_data: bool
