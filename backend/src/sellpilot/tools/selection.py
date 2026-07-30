from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sellpilot.core.enums import SiteCode, ToolCallerType, ToolRiskLevel
from sellpilot.core.exceptions import ParameterError, UnauthenticatedError
from sellpilot.domain.selection.models import SelectionCandidate
from sellpilot.domain.selection.scoring import calculate_profit
from sellpilot.schemas.selection import SelectionAnalysisRequest, SelectionCandidateQuery
from sellpilot.services.product_improvement import ProductImprovementService
from sellpilot.services.selection import SelectionService
from sellpilot.tools.contracts import (
    RetryPolicy,
    ToolDefinition,
    ToolExecutionContext,
)
from sellpilot.tools.registry import ToolRegistry


class ToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchMarketProductsInput(ToolModel):
    site: SiteCode
    category_id: str | None = None
    category_query: str | None = Field(default=None, min_length=1, max_length=100)
    product_ids: list[str] | None = Field(default=None, min_length=1, max_length=100)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, gt=0)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class SearchMarketProductsOutput(ToolModel):
    products: list[dict[str, object]]
    count: int
    is_mock_data: bool = True


class CalculateProductProfitInput(ToolModel):
    candidate: SelectionCandidate


class CalculateProductProfitOutput(ToolModel):
    profit: dict[str, object]
    formula_version: str


class ScoreProductOpportunityInput(SelectionAnalysisRequest):
    pass


class ScoreProductOpportunityOutput(ToolModel):
    analysis: dict[str, object]
    candidate_search: dict[str, object]
    no_data: bool = False
    message: str | None = None


class CompareProductsInput(ToolModel):
    task_id: UUID
    product_ids: list[str] = Field(min_length=2, max_length=10)

    @field_validator("product_ids")
    @classmethod
    def require_unique_product_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("product_ids must be unique")
        return value


class CompareProductsOutput(ToolModel):
    products: list[dict[str, object]]


class ExportProductAnalysisReportInput(ToolModel):
    task_id: UUID | None = None
    improvement_report_id: UUID | None = None

    @model_validator(mode="after")
    def require_one_report_source(self):
        if (self.task_id is None) == (self.improvement_report_id is None):
            raise ValueError("provide exactly one of task_id or improvement_report_id")
        return self


class ExportProductAnalysisReportOutput(ToolModel):
    report: dict[str, object]


def _service(context: ToolExecutionContext) -> SelectionService:
    if context.session is None:
        raise ParameterError("selection tools require a database session")
    return SelectionService(context.session)


def _user_id(context: ToolExecutionContext) -> UUID:
    if context.user_id is None:
        raise UnauthenticatedError()
    return context.user_id


async def _search(payload: SearchMarketProductsInput, context: ToolExecutionContext):
    products = await _service(context).list_candidates(
        SelectionCandidateQuery.model_validate(payload.model_dump())
    )
    return SearchMarketProductsOutput(
        products=[item.model_dump(mode="json") for item in products],
        count=len(products),
    )


async def _profit(payload: CalculateProductProfitInput, _context: ToolExecutionContext):
    profit = calculate_profit(payload.candidate)
    return CalculateProductProfitOutput(
        profit=profit.model_dump(mode="json"),
        formula_version="selection-v1.0.0",
    )


async def _score(payload: ScoreProductOpportunityInput, context: ToolExecutionContext):
    result = await _service(context).analyze(
        payload,
        _user_id(context),
        agent_task_id=(context.task_id if context.caller_type is ToolCallerType.WORKFLOW else None),
        manage_agent_task=context.caller_type is not ToolCallerType.WORKFLOW,
    )
    normalized_filters = {
        "site": payload.site.value,
        "category_id": payload.category_id,
        "category_query": payload.category_query,
        "min_price": payload.min_price,
        "max_price": payload.max_price,
        "limit": payload.limit,
    }
    return ScoreProductOpportunityOutput(
        analysis=result.model_dump(mode="json"),
        candidate_search={
            "count": result.total_candidates,
            "matched_count": result.total_candidates,
            "is_mock_data": result.is_mock_data,
            "normalized_filters": normalized_filters,
        },
    )


async def _compare(payload: CompareProductsInput, context: ToolExecutionContext):
    result = await _service(context).compare(
        payload.task_id, payload.product_ids, _user_id(context)
    )
    return CompareProductsOutput(products=[item.model_dump(mode="json") for item in result])


async def _export(payload: ExportProductAnalysisReportInput, context: ToolExecutionContext):
    if payload.improvement_report_id is not None:
        if context.session is None:
            raise ParameterError("product improvement export requires a database session")
        result = await ProductImprovementService(context.session).export(
            payload.improvement_report_id, _user_id(context)
        )
        return ExportProductAnalysisReportOutput(report=result)
    result = await _service(context).export(payload.task_id, _user_id(context))
    return ExportProductAnalysisReportOutput(report=result.model_dump(mode="json"))


def build_selection_tools() -> tuple[ToolDefinition, ...]:
    retry_policy = RetryPolicy(
        max_attempts=1,
        initial_delay_ms=0,
        max_delay_ms=0,
        backoff_multiplier=1,
    )
    return (
        ToolDefinition(
            name="search_market_products",
            version="1.0.0",
            description="Search validated Mock Shopee candidate products.",
            input_schema=SearchMarketProductsInput,
            output_schema=SearchMarketProductsOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=10,
            retry_policy=retry_policy,
            idempotent=True,
            expose_to_mcp=False,
            handler=_search,
        ),
        ToolDefinition(
            name="calculate_product_profit",
            version="1.0.0",
            description="Calculate deterministic product profit and margin.",
            input_schema=CalculateProductProfitInput,
            output_schema=CalculateProductProfitOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=5,
            retry_policy=retry_policy,
            idempotent=True,
            expose_to_mcp=False,
            handler=_profit,
        ),
        ToolDefinition(
            name="score_product_opportunity",
            version="1.0.0",
            description="Run and persist an internally traceable deterministic selection analysis.",
            input_schema=ScoreProductOpportunityInput,
            output_schema=ScoreProductOpportunityOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=30,
            retry_policy=retry_policy,
            idempotent=False,
            expose_to_mcp=False,
            handler=_score,
        ),
        ToolDefinition(
            name="compare_products",
            version="1.0.0",
            description="Compare persisted results from one owned selection task.",
            input_schema=CompareProductsInput,
            output_schema=CompareProductsOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=10,
            retry_policy=retry_policy,
            idempotent=True,
            expose_to_mcp=False,
            handler=_compare,
        ),
        ToolDefinition(
            name="export_product_analysis_report",
            version="1.1.0",
            description=(
                "Serialize an existing selection or product-improvement report "
                "without writing a server file."
            ),
            input_schema=ExportProductAnalysisReportInput,
            output_schema=ExportProductAnalysisReportOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=10,
            retry_policy=retry_policy,
            idempotent=True,
            expose_to_mcp=False,
            handler=_export,
        ),
    )


def register_selection_tools(registry: ToolRegistry) -> None:
    for definition in build_selection_tools():
        registry.register(definition)
