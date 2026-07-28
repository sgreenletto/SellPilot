from uuid import UUID

from pydantic import BaseModel, ConfigDict

from sellpilot.core.enums import ToolCallerType, ToolRiskLevel
from sellpilot.core.exceptions import ParameterError, UnauthenticatedError
from sellpilot.schemas.review_analysis import (
    ReviewAnalysisCreateRequest,
    ReviewQuery,
)
from sellpilot.services.review_analysis import ReviewAnalysisService
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition, ToolExecutionContext
from sellpilot.tools.registry import ToolRegistry


class ToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GetProductReviewsInput(ReviewQuery):
    pass


class GetProductReviewsOutput(ToolModel):
    reviews: list[dict[str, object]]
    count: int
    is_mock_data: bool


class AnalyzeProductReviewsInput(ReviewAnalysisCreateRequest):
    pass


class AnalyzeProductReviewsOutput(ToolModel):
    analysis: dict[str, object]


def _service(context: ToolExecutionContext) -> ReviewAnalysisService:
    if context.session is None:
        raise ParameterError("review analysis tools require a database session")
    if context.settings is None:
        raise ParameterError("review analysis tools require runtime settings")
    return ReviewAnalysisService(context.session, context.settings)


def _user_id(context: ToolExecutionContext) -> UUID:
    if context.user_id is None:
        raise UnauthenticatedError()
    return context.user_id


async def _get_reviews(
    payload: GetProductReviewsInput,
    context: ToolExecutionContext,
):
    reviews = await _service(context).list_reviews(ReviewQuery.model_validate(payload.model_dump()))
    return GetProductReviewsOutput(
        reviews=[item.model_dump(mode="json") for item in reviews],
        count=len(reviews),
        is_mock_data=all(item.is_mock_data for item in reviews),
    )


async def _analyze(
    payload: AnalyzeProductReviewsInput,
    context: ToolExecutionContext,
):
    service = _service(context)
    workflow_owned = context.caller_type is ToolCallerType.WORKFLOW and context.task_id is not None
    created = await service.create(
        ReviewAnalysisCreateRequest.model_validate(payload.model_dump()),
        _user_id(context),
        agent_task_id=context.task_id if workflow_owned else None,
    )
    result = await service.run(
        created.analysis_id,
        _user_id(context),
        manage_agent_task=not (workflow_owned and created.agent_task_id == context.task_id),
    )
    return AnalyzeProductReviewsOutput(analysis=result.model_dump(mode="json"))


def build_review_analysis_tools() -> tuple[ToolDefinition, ...]:
    retry_policy = RetryPolicy(
        max_attempts=1,
        initial_delay_ms=0,
        max_delay_ms=0,
        backoff_multiplier=1,
    )
    return (
        ToolDefinition(
            name="get_product_reviews",
            version="1.0.0",
            description="Read a bounded page of validated Mock Shopee product reviews.",
            input_schema=GetProductReviewsInput,
            output_schema=GetProductReviewsOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=10,
            retry_policy=retry_policy,
            idempotent=True,
            expose_to_mcp=False,
            handler=_get_reviews,
        ),
        ToolDefinition(
            name="analyze_product_reviews",
            version="1.0.0",
            description=(
                "Run and persist an evidence-bound review analysis through an internal "
                "AgentTask workflow."
            ),
            input_schema=AnalyzeProductReviewsInput,
            output_schema=AnalyzeProductReviewsOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=30,
            retry_policy=retry_policy,
            idempotent=False,
            expose_to_mcp=False,
            handler=_analyze,
        ),
    )


def register_review_analysis_tools(registry: ToolRegistry) -> None:
    for definition in build_review_analysis_tools():
        registry.register(definition)
