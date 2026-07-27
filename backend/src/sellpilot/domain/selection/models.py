from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SelectionMetric(StrEnum):
    DEMAND = "demand"
    COMPETITION = "competition"
    PROFITABILITY = "profitability"
    REVIEW_QUALITY = "review_quality"
    LOGISTICS = "logistics"
    AFTER_SALES = "after_sales"
    FACTORY_FIT = "factory_fit"


class SelectionCandidate(BaseModel):
    """Validated, source-agnostic input consumed by the deterministic scorer."""

    model_config = ConfigDict(frozen=True)

    product_id: str = Field(min_length=1, max_length=100)
    site: str = Field(min_length=1, max_length=64)
    currency: str = Field(min_length=3, max_length=8)
    source_type: str = Field(min_length=1, max_length=64)
    is_mock_data: bool
    price: Decimal = Field(gt=0)
    cost: Decimal = Field(ge=0)
    shipping_cost: Decimal = Field(ge=0)
    platform_fee_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    other_costs: Decimal = Field(default=Decimal("0"), ge=0)
    sales_count: int | None = Field(default=None, ge=0)
    search_index: Decimal | None = Field(default=None, ge=0)
    sales_index: Decimal | None = Field(default=None, ge=0)
    growth_rate: Decimal | None = None
    competition_index: Decimal | None = Field(default=None, ge=0)
    rating: Decimal | None = Field(default=None, ge=0, le=5)
    review_count: int | None = Field(default=None, ge=0)
    logistics_risk_rate: Decimal | None = Field(default=None, ge=0, le=1)
    after_sales_rate: Decimal | None = Field(default=None, ge=0, le=1)
    factory_fit_score: Decimal | None = Field(default=None, ge=0, le=1)

    @field_validator("product_id", "site", "currency", "source_type")
    @classmethod
    def strip_non_empty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_review_pair(self) -> "SelectionCandidate":
        if (self.rating is None) != (self.review_count is None):
            raise ValueError("rating and review_count must be supplied together")
        if self.rating is not None and self.review_count is not None:
            if self.review_count == 0 and self.rating != 0:
                raise ValueError("rating must be 0 when review_count is 0")
            if self.review_count > 0 and self.rating < 1:
                raise ValueError("rating must be between 1 and 5 when reviews exist")
        return self


class SelectionCriteria(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_profit: Decimal = Decimal("0")
    minimum_margin: Decimal = Field(default=Decimal("0"), ge=-1, le=1)


class SelectionFormulaConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1, max_length=64)
    weights: dict[SelectionMetric, Decimal]
    neutral_score: Decimal = Field(default=Decimal("50"), ge=0, le=100)
    score_quantum: Decimal = Field(default=Decimal("0.0001"), gt=0)
    money_quantum: Decimal = Field(default=Decimal("0.01"), gt=0)
    growth_floor: Decimal = Decimal("-1")
    growth_ceiling: Decimal = Decimal("2")
    review_rating_weight: Decimal = Field(default=Decimal("0.8"), ge=0, le=1)
    review_volume_weight: Decimal = Field(default=Decimal("0.2"), ge=0, le=1)

    @model_validator(mode="after")
    def validate_config(self) -> "SelectionFormulaConfig":
        expected = set(SelectionMetric)
        actual = set(self.weights)
        if actual != expected:
            missing = sorted(metric.value for metric in expected - actual)
            unknown = sorted(str(metric) for metric in actual - expected)
            raise ValueError(
                f"weights must contain every known metric; missing={missing}, unknown={unknown}"
            )
        if any(weight < 0 for weight in self.weights.values()):
            raise ValueError("weights must not be negative")
        if sum(self.weights.values(), Decimal("0")) != Decimal("1"):
            raise ValueError("weights must sum exactly to 1")
        if self.growth_floor >= self.growth_ceiling:
            raise ValueError("growth_floor must be less than growth_ceiling")
        if self.review_rating_weight + self.review_volume_weight != Decimal("1"):
            raise ValueError("review component weights must sum exactly to 1")
        return self


class ProfitBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    price: Decimal
    cost: Decimal
    shipping_cost: Decimal
    platform_fee: Decimal
    other_costs: Decimal
    total_cost: Decimal
    profit: Decimal
    margin: Decimal


class MetricEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: Decimal | None
    configured_weight: Decimal
    effective_weight: Decimal
    inputs: dict[str, Decimal | int | None]
    formula: str
    missing_reason: str | None = None


class CandidateScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: str
    site: str
    currency: str
    source_type: str
    is_mock_data: bool
    rank: int
    cohort_rank: int
    total_score: Decimal
    data_completeness: Decimal
    confidence: Decimal
    profit: ProfitBreakdown
    metrics: dict[SelectionMetric, MetricEvidence]
    recommendation_facts: tuple[str, ...]
    risk_warnings: tuple[str, ...]
    formula_version: str


class CandidateExclusion(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: str
    site: str
    currency: str
    reasons: tuple[str, ...]
    profit: ProfitBreakdown
    formula_version: str


class SelectionBatchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    formula_version: str
    ranked: tuple[CandidateScore, ...]
    excluded: tuple[CandidateExclusion, ...]
    cohort_keys: tuple[str, ...]
