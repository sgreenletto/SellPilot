from uuid import UUID

from pydantic import BaseModel, ConfigDict

from sellpilot.core.enums import ToolCallerType, ToolRiskLevel
from sellpilot.core.exceptions import (
    ExternalServiceUnavailableError,
    ParameterError,
    UnauthenticatedError,
)
from sellpilot.domain.content_generation.models import (
    ListingFacts,
    LocalizedListing,
)
from sellpilot.domain.content_generation.workflow import check_listing
from sellpilot.schemas.content_generation import ContentGenerateRequest
from sellpilot.services.content_generation import ContentGenerationService
from sellpilot.services.model_gateway import ModelGatewayError
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition, ToolExecutionContext
from sellpilot.tools.registry import ToolRegistry


class ToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenerateLocalizedListingInput(ContentGenerateRequest):
    pass


class GenerateLocalizedListingOutput(ToolModel):
    generation: dict[str, object]
    facts: ListingFacts


class CheckListingComplianceInput(ToolModel):
    facts: ListingFacts
    content: LocalizedListing


class CheckListingComplianceOutput(ToolModel):
    quality: dict[str, object]


def _service(context: ToolExecutionContext) -> ContentGenerationService:
    if context.session is None or context.settings is None:
        raise ParameterError("content tools require database session and settings")
    return ContentGenerationService(context.session, context.settings)


def _user(context: ToolExecutionContext) -> UUID:
    if context.user_id is None:
        raise UnauthenticatedError()
    return context.user_id


async def _generate(payload: GenerateLocalizedListingInput, context: ToolExecutionContext):
    service = _service(context)
    request = ContentGenerateRequest.model_validate(payload.model_dump())
    workflow_owned = context.caller_type is ToolCallerType.WORKFLOW and context.task_id is not None
    facts = await service.get_listing_facts(request)
    try:
        result = await service.generate(
            request,
            _user(context),
            agent_task_id=context.task_id if workflow_owned else None,
            manage_agent_task=not workflow_owned,
        )
    except ModelGatewayError as exc:
        raise ExternalServiceUnavailableError("Content generation provider is unavailable") from exc
    return GenerateLocalizedListingOutput(
        generation=result.model_dump(mode="json"),
        facts=facts,
    )


async def _check(payload: CheckListingComplianceInput, _context: ToolExecutionContext):
    result = check_listing(payload.content, payload.facts, 1)
    return CheckListingComplianceOutput(quality=result.model_dump(mode="json"))


def build_content_generation_tools() -> tuple[ToolDefinition, ...]:
    retry = RetryPolicy(
        max_attempts=1,
        initial_delay_ms=0,
        max_delay_ms=0,
        backoff_multiplier=1,
    )
    return (
        ToolDefinition(
            name="generate_localized_listing",
            version="1.0.0",
            description="Generate schema-validated localized content from Mock product facts.",
            input_schema=GenerateLocalizedListingInput,
            output_schema=GenerateLocalizedListingOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=30,
            retry_policy=retry,
            idempotent=False,
            expose_to_mcp=False,
            handler=_generate,
        ),
        ToolDefinition(
            name="check_listing_compliance",
            version="1.0.0",
            description="Run deterministic fact, completeness, and compliance checks.",
            input_schema=CheckListingComplianceInput,
            output_schema=CheckListingComplianceOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=10,
            retry_policy=retry,
            idempotent=True,
            expose_to_mcp=False,
            handler=_check,
        ),
    )


def register_content_generation_tools(registry: ToolRegistry) -> None:
    for definition in build_content_generation_tools():
        registry.register(definition)
