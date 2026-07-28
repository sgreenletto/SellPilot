from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from sellpilot.core.enums import AnalysisStatus, CurrencyCode, SiteCode
from sellpilot.schemas.common import ContractModel

SelectionSortField = Literal["sales_count", "rating", "review_count", "price", "updated_at"]


class SelectionCandidateQuery(ContractModel):
    site: SiteCode
    category_id: str | None = Field(default=None, min_length=1, max_length=100)
    product_ids: list[str] | None = Field(default=None, min_length=1, max_length=100)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, gt=0)
    sort_by: SelectionSortField = "sales_count"
    descending: bool = True
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=100)

    @model_validator(mode="after")
    def validate_price_range(self) -> "SelectionCandidateQuery":
        if self.min_price is not None and self.max_price is not None:
            if self.min_price > self.max_price:
                raise ValueError("min_price must not exceed max_price")
        return self


class SelectionAnalysisRequest(SelectionCandidateQuery):
    minimum_profit: Decimal = Decimal("0")
    minimum_margin: Decimal = Field(default=Decimal("0"), ge=-1, le=1)
    platform_fee_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    other_costs: Decimal = Field(default=Decimal("0"), ge=0)


class SelectionCandidateResponse(ContractModel):
    product_id: str
    title: str
    category_id: str
    category_name: str
    site: SiteCode
    currency: CurrencyCode
    price: Decimal
    cost: Decimal
    shipping_cost: Decimal
    sales_count: int
    rating: Decimal
    review_count: int
    search_index: Decimal | None = None
    sales_index: Decimal | None = None
    competition_index: Decimal | None = None
    growth_rate: Decimal | None = None
    source_name: str
    is_mock_data: bool


class SelectionResultResponse(ContractModel):
    id: UUID
    product_id: str
    title: str | None = None
    rank: int
    total_score: Decimal
    data_completeness: Decimal
    currency: CurrencyCode
    site: SiteCode
    profit: dict[str, object]
    metrics: dict[str, object]
    explanation: dict[str, object]
    risk_warnings: list[str]
    evidence: dict[str, object]
    is_mock_data: bool


class SelectionAnalysisResponse(ContractModel):
    task_id: UUID
    agent_task_id: UUID
    status: AnalysisStatus
    formula_version: str
    generation_mode: Literal["rule_template", "validated_generator"]
    total_candidates: int
    ranked_count: int
    excluded_count: int
    results: list[SelectionResultResponse]
    excluded: list[dict[str, object]]
    is_mock_data: bool


class SelectionTaskResponse(ContractModel):
    task_id: UUID
    agent_task_id: UUID | None
    status: AnalysisStatus
    criteria: dict[str, object]
    formula_version: str
    is_mock_data: bool
    results: list[SelectionResultResponse]


class SelectionExportResponse(ContractModel):
    filename: str
    content_type: Literal["application/json"]
    checksum_sha256: str
    task: SelectionTaskResponse
