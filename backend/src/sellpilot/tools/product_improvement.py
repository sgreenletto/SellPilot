from uuid import UUID

from pydantic import BaseModel, ConfigDict

from sellpilot.core.enums import ToolRiskLevel
from sellpilot.core.exceptions import ParameterError, UnauthenticatedError
from sellpilot.services.product_improvement import ProductImprovementService
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition, ToolExecutionContext
from sellpilot.tools.registry import ToolRegistry


class ToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenerateImprovementInput(ToolModel):
    analysis_id: UUID


class ImprovementToolOutput(ToolModel):
    report: dict[str, object]


def _service(context: ToolExecutionContext) -> ProductImprovementService:
    if context.session is None:
        raise ParameterError("product improvement tools require a database session")
    return ProductImprovementService(context.session)


def _user_id(context: ToolExecutionContext) -> UUID:
    if context.user_id is None:
        raise UnauthenticatedError()
    return context.user_id


async def _generate(payload: GenerateImprovementInput, context: ToolExecutionContext):
    result = await _service(context).generate(payload.analysis_id, _user_id(context))
    return ImprovementToolOutput(report=result.model_dump(mode="json"))


def build_product_improvement_tools() -> tuple[ToolDefinition, ...]:
    retry = RetryPolicy(
        max_attempts=1,
        initial_delay_ms=0,
        max_delay_ms=0,
        backoff_multiplier=1,
    )
    return (
        ToolDefinition(
            name="generate_product_improvement_plan",
            version="1.0.0",
            description="Generate a deterministic evidence-bound product improvement report.",
            input_schema=GenerateImprovementInput,
            output_schema=ImprovementToolOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=20,
            retry_policy=retry,
            idempotent=True,
            expose_to_mcp=False,
            handler=_generate,
        ),
    )


def register_product_improvement_tools(registry: ToolRegistry) -> None:
    for definition in build_product_improvement_tools():
        registry.register(definition)
