from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from sellpilot.core.enums import ToolRiskLevel
from sellpilot.core.exceptions import ParameterError
from sellpilot.services.customer_service import CustomerServiceService
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition, ToolExecutionContext
from sellpilot.tools.registry import ToolRegistry


class CustomerToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GetCustomerConversationInput(CustomerToolModel):
    session_id: str = Field(min_length=1, max_length=100)


class GetCustomerConversationOutput(CustomerToolModel):
    context: dict[str, object]


class ClassifyCustomerRequestInput(CustomerToolModel):
    context: dict[str, object]
    buyer_message: str | None = Field(default=None, max_length=2000)


class ClassifyCustomerRequestOutput(CustomerToolModel):
    classification: dict[str, object]


class DraftCustomerReplyInput(CustomerToolModel):
    context: dict[str, object]
    classification: dict[str, object]
    evidence: dict[str, object]


class DraftCustomerReplyOutput(CustomerToolModel):
    draft: dict[str, object]


class MockSendCustomerReplyInput(CustomerToolModel):
    session_id: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=4000)


class MockSendCustomerReplyOutput(CustomerToolModel):
    message_id: str
    session_id: str
    status: str
    sent_at: datetime
    is_mock_data: bool


def _service(context: ToolExecutionContext) -> CustomerServiceService:
    if context.session is None or context.settings is None:
        raise ParameterError("customer service tools require database session and settings")
    return CustomerServiceService(context.session, context.settings)


async def _get_conversation(
    payload: GetCustomerConversationInput,
    context: ToolExecutionContext,
) -> GetCustomerConversationOutput:
    return GetCustomerConversationOutput(
        context=await _service(context).get_context(payload.session_id)
    )


async def _classify(
    payload: ClassifyCustomerRequestInput,
    context: ToolExecutionContext,
) -> ClassifyCustomerRequestOutput:
    return ClassifyCustomerRequestOutput(
        classification=_service(context).classify(payload.context, payload.buyer_message)
    )


async def _draft(
    payload: DraftCustomerReplyInput,
    context: ToolExecutionContext,
) -> DraftCustomerReplyOutput:
    return DraftCustomerReplyOutput(
        draft=_service(context).draft(
            payload.context,
            payload.classification,
            payload.evidence,
        )
    )


async def _mock_send(
    payload: MockSendCustomerReplyInput,
    context: ToolExecutionContext,
) -> MockSendCustomerReplyOutput:
    return MockSendCustomerReplyOutput.model_validate(
        await _service(context).send_mock(payload.session_id, payload.content)
    )


def build_customer_service_tools() -> tuple[ToolDefinition, ...]:
    read_retry = RetryPolicy(
        max_attempts=1,
        initial_delay_ms=0,
        max_delay_ms=0,
        backoff_multiplier=1,
    )
    shared = {
        "version": "1.0.0",
        "retry_policy": read_retry,
        "expose_to_mcp": False,
    }
    return (
        ToolDefinition(
            name="get_customer_conversation",
            description="Read one Mock customer session and its bounded message history.",
            input_schema=GetCustomerConversationInput,
            output_schema=GetCustomerConversationOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=10,
            idempotent=True,
            handler=_get_conversation,
            **shared,
        ),
        ToolDefinition(
            name="classify_customer_request",
            description=(
                "Classify customer intent, risk, and the evidence branch deterministically."
            ),
            input_schema=ClassifyCustomerRequestInput,
            output_schema=ClassifyCustomerRequestOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=10,
            idempotent=True,
            handler=_classify,
            **shared,
        ),
        ToolDefinition(
            name="draft_customer_reply",
            description="Draft a reply only from the selected branch's verified evidence.",
            input_schema=DraftCustomerReplyInput,
            output_schema=DraftCustomerReplyOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=10,
            idempotent=True,
            handler=_draft,
            **shared,
        ),
        ToolDefinition(
            name="mock_send_customer_reply",
            description="Send a confirmed reply to the Mock Shopee conversation only.",
            input_schema=MockSendCustomerReplyInput,
            output_schema=MockSendCustomerReplyOutput,
            risk_level=ToolRiskLevel.HIGH_RISK,
            timeout_seconds=10,
            idempotent=True,
            handler=_mock_send,
            **shared,
        ),
    )


def register_customer_service_tools(registry: ToolRegistry) -> None:
    for definition in build_customer_service_tools():
        registry.register(definition)
