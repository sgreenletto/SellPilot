from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sellpilot.core.config import Settings
from sellpilot.core.enums import TaskStepStatus, TaskType, WorkflowNodeType
from sellpilot.schemas.commerce import OrderResponse
from sellpilot.schemas.content_generation import ContentGenerateRequest
from sellpilot.schemas.replenishment import (
    ReplenishmentAnalysisOutput,
    ReplenishmentAnalysisRequest,
)
from sellpilot.schemas.review_analysis import ReviewAnalysisCreateRequest
from sellpilot.schemas.selection import SelectionAnalysisRequest
from sellpilot.tools.commerce import (
    GetOrderInput,
    GetOrderLogisticsInput,
    GetOrderLogisticsOutput,
    GetProductInput,
    ListInventoryOutput,
    ListLowStockInput,
    ListOrdersInput,
)
from sellpilot.tools.content_generation import CheckListingComplianceInput
from sellpilot.tools.customer_service import (
    ClassifyCustomerRequestInput,
    DraftCustomerReplyInput,
    GetCustomerConversationInput,
    MockSendCustomerReplyInput,
)
from sellpilot.tools.knowledge import SearchKnowledgeInput, SearchKnowledgeOutput
from sellpilot.tools.product_improvement import GenerateImprovementInput, ImprovementToolOutput
from sellpilot.tools.review_analysis import AnalyzeProductReviewsInput, AnalyzeProductReviewsOutput
from sellpilot.tools.selection import SearchMarketProductsInput
from sellpilot.tools.system import SystemHealthOutput
from sellpilot.workflows.contracts import (
    NodeDefinition,
    NodeExecutionResult,
    TaskExecutionContext,
    WorkflowDefinition,
)
from sellpilot.workflows.registry import WorkflowRegistry


class WorkflowModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiagnosticWorkflowInput(WorkflowModel):
    message: str = Field(default="ok", min_length=1, max_length=200)


class DiagnosticWorkflowOutput(WorkflowModel):
    status: str
    diagnostic: bool
    message: str


class SystemHealthWorkflowInput(WorkflowModel):
    pass


class OrderQueryWorkflowInput(WorkflowModel):
    order_id: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = Field(default=None, max_length=32)
    shop_id: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=20, ge=1, le=100)


class OrderQueryWorkflowOutput(WorkflowModel):
    mode: Literal["single", "list"]
    order: OrderResponse | None = None
    orders: list[OrderResponse] = Field(default_factory=list)
    count: int = Field(ge=0)
    is_mock_data: bool

    @model_validator(mode="after")
    def validate_mode_payload(self) -> "OrderQueryWorkflowOutput":
        if self.mode == "single" and (self.order is None or self.orders or self.count != 1):
            raise ValueError("single order results require exactly one order")
        if self.mode == "list" and (self.order is not None or self.count != len(self.orders)):
            raise ValueError("order list results require a matching count")
        return self


class SelectionWorkflowOutput(WorkflowModel):
    analysis: dict[str, object] | None = None
    candidate_search: dict[str, object]
    no_data: bool = False
    message: str | None = None


class ContentWorkflowOutput(WorkflowModel):
    generation: dict[str, object]
    compliance: dict[str, object]
    loop: dict[str, object]


class ProductImprovementWorkflowInput(WorkflowModel):
    product_id: str | None = Field(default=None, min_length=1, max_length=100)
    analysis_id: UUID | None = None

    @model_validator(mode="after")
    def require_source(self) -> "ProductImprovementWorkflowInput":
        if self.product_id is None and self.analysis_id is None:
            raise ValueError("product_id or analysis_id is required")
        return self


class CustomerServiceWorkflowInput(WorkflowModel):
    session_id: str = Field(min_length=1, max_length=100)
    buyer_message: str | None = Field(default=None, max_length=2000)
    simulate_send: bool = False


class CustomerServiceWorkflowOutput(WorkflowModel):
    draft: dict[str, object]
    classification: dict[str, object]
    evidence: dict[str, object]
    simulated_send: dict[str, object] | None = None


async def _selection_search_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    payload = SearchMarketProductsInput(
        site=context.workflow_input["site"],
        category_id=context.workflow_input.get("category_id"),
        category_query=context.workflow_input.get("category_query"),
        product_ids=context.workflow_input.get("product_ids"),
        min_price=context.workflow_input.get("min_price"),
        max_price=context.workflow_input.get("max_price"),
        offset=int(context.workflow_input.get("offset", 0)),
        limit=min(int(context.workflow_input.get("limit", 20)), 50),
    )
    return NodeExecutionResult(tool_input=payload.model_dump(mode="json"))


async def _select_selection_candidate_branch(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    search = dict(context.state.get("last_output") or {})
    products = search.get("products")
    product_rows = products if isinstance(products, list) else []
    product_ids = [
        str(item["product_id"])
        for item in product_rows
        if isinstance(item, dict) and item.get("product_id")
    ]
    candidate_search = {
        "count": len(product_ids),
        "matched_count": len(product_ids),
        "is_mock_data": bool(search.get("is_mock_data", True)),
        "normalized_filters": {
            key: context.workflow_input.get(key)
            for key in (
                "site",
                "category_id",
                "category_query",
                "min_price",
                "max_price",
                "limit",
            )
        },
    }
    has_candidates = bool(product_ids)
    selected = "score_product_opportunity" if has_candidates else "finish_selection_no_data"
    return NodeExecutionResult(
        output={"selected_branch": selected, "candidate_count": len(product_ids)},
        state_updates={
            "candidate_search": candidate_search,
            "selection_candidate_ids": product_ids,
        },
        next_node=selected,
    )


async def _selection_score_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    candidate_ids = context.state.get("selection_candidate_ids")
    product_ids = [str(item) for item in candidate_ids] if isinstance(candidate_ids, list) else []
    payload = dict(context.workflow_input)
    payload["product_ids"] = product_ids
    payload["offset"] = 0
    payload["limit"] = len(product_ids)
    return NodeExecutionResult(tool_input=payload)


async def _finish_selection_no_data(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    candidate_search = dict(context.state.get("candidate_search") or {})
    candidate_search.update(
        {
            "reason": "no_matching_candidates",
            "suggestion": "请调整站点或商品类目后重试。",
        }
    )
    return NodeExecutionResult(
        output={
            "analysis": None,
            "candidate_search": candidate_search,
            "no_data": True,
            "message": "当前数据中没有匹配的候选商品，请调整站点或商品类目。",
        }
    )


async def _content_compliance_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    generated = dict(context.state.get("last_output") or {})
    generation = dict(generated.get("generation") or {})
    result = dict(generation.get("result") or {})
    payload = CheckListingComplianceInput(
        facts=generated["facts"],
        content=result["content"],
    )
    return NodeExecutionResult(
        tool_input=payload.model_dump(mode="json"),
        state_updates={
            "content_generation": generation,
            "content_facts": generated["facts"],
        },
    )


async def _validate_content_quality(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    compliance = dict(context.state.get("last_output") or {}).get("quality")
    quality = dict(compliance) if isinstance(compliance, dict) else {}
    if not quality.get("passed"):
        return NodeExecutionResult(
            status=TaskStepStatus.FAILED,
            error_code="CONTENT_QUALITY_FAILED",
            error_message="内容生成在最多三轮后仍未通过事实与合规检查",
            retryable=False,
        )
    return NodeExecutionResult(
        output={"selected_branch": "finish_content_generation"},
        state_updates={"content_compliance": quality},
        next_node="finish_content_generation",
    )


async def _finish_content_generation(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    generation = dict(context.state.get("content_generation") or {})
    result = dict(generation.get("result") or {})
    generated_quality = dict(result.get("quality") or {})
    attempt_history = result.get("attempt_history")
    attempts_log = attempt_history if isinstance(attempt_history, list) else []
    compliance = dict(context.state.get("content_compliance") or {})
    attempts = int(generated_quality.get("attempts", 0))
    final_attempt = attempts_log[-1] if attempts_log and isinstance(attempts_log[-1], dict) else {}
    return NodeExecutionResult(
        output={
            "generation": generation,
            "compliance": compliance,
            "loop": {
                "attempts": attempts,
                "max_attempts": int(context.workflow_input.get("max_attempts", 3)),
                "stop_reason": final_attempt.get("stop_reason", "quality_passed"),
                "is_bounded": True,
                "attempt_history": attempts_log,
            },
        }
    )


async def _select_improvement_source(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    selected = (
        "generate_product_improvement_plan"
        if context.workflow_input.get("analysis_id")
        else "analyze_reviews_for_improvement"
    )
    return NodeExecutionResult(
        output={"selected_branch": selected},
        next_node=selected,
    )


async def _improvement_review_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    payload = AnalyzeProductReviewsInput(
        product_id=str(context.workflow_input["product_id"]),
        idempotency_key=f"assistant-improvement-{context.task_id}",
    )
    return NodeExecutionResult(tool_input=payload.model_dump(mode="json"))


async def _improvement_generate_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    analysis_id = context.workflow_input.get("analysis_id")
    if analysis_id is None:
        review_output = dict(context.state.get("last_output") or {})
        analysis = dict(review_output.get("analysis") or {})
        analysis_id = analysis.get("analysis_id")
    return NodeExecutionResult(
        tool_input=GenerateImprovementInput(analysis_id=analysis_id).model_dump(mode="json")
    )


async def _customer_context_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    payload = GetCustomerConversationInput(session_id=context.workflow_input["session_id"])
    return NodeExecutionResult(tool_input=payload.model_dump(mode="json"))


async def _customer_classification_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    previous = dict(context.state.get("last_output") or {})
    conversation = dict(previous.get("context") or {})
    payload = ClassifyCustomerRequestInput(
        context=conversation,
        buyer_message=context.workflow_input.get("buyer_message"),
    )
    return NodeExecutionResult(
        tool_input=payload.model_dump(mode="json"),
        state_updates={"customer_context": conversation},
    )


async def _select_customer_branch(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    previous = dict(context.state.get("last_output") or {})
    classification = dict(previous.get("classification") or {})
    branch = str(classification.get("branch") or "human")
    routes = {
        "human": "record_customer_handoff",
        "policy": "search_customer_knowledge",
        "order": "get_customer_order",
        "logistics": "get_customer_logistics",
        "product": "get_customer_product",
    }
    selected = routes.get(branch, "record_customer_handoff")
    return NodeExecutionResult(
        output={
            "selected_branch": branch,
            "reason": classification.get("reason"),
            "risk_level": classification.get("risk_level"),
        },
        state_updates={"customer_classification": classification},
        next_node=selected,
    )


async def _record_customer_handoff(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    return NodeExecutionResult(
        output={"requires_human": True, "reason": "high_risk_or_low_confidence"}
    )


async def _customer_knowledge_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    classification = dict(context.state.get("customer_classification") or {})
    payload = SearchKnowledgeInput(
        query=str(classification.get("query") or "店铺政策"),
        top_k=5,
        category="policy",
    )
    return NodeExecutionResult(tool_input=payload.model_dump(mode="json"))


async def _customer_order_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    conversation = dict(context.state.get("customer_context") or {})
    payload = GetOrderInput(order_id=str(conversation["order_id"]))
    return NodeExecutionResult(tool_input=payload.model_dump(mode="json"))


async def _customer_logistics_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    conversation = dict(context.state.get("customer_context") or {})
    payload = GetOrderLogisticsInput(order_id=str(conversation["order_id"]))
    return NodeExecutionResult(tool_input=payload.model_dump(mode="json"))


async def _customer_product_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    conversation = dict(context.state.get("customer_context") or {})
    payload = GetProductInput(product_id=str(conversation["product_id"]))
    return NodeExecutionResult(tool_input=payload.model_dump(mode="json"))


async def _customer_draft_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    evidence = dict(context.state.get("last_output") or {})
    payload = DraftCustomerReplyInput(
        context=dict(context.state.get("customer_context") or {}),
        classification=dict(context.state.get("customer_classification") or {}),
        evidence=evidence,
    )
    return NodeExecutionResult(
        tool_input=payload.model_dump(mode="json"),
        state_updates={"customer_evidence": evidence},
    )


async def _select_customer_send_branch(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    previous = dict(context.state.get("last_output") or {})
    draft = dict(previous.get("draft") or {})
    should_send = bool(context.workflow_input.get("simulate_send")) and bool(
        draft.get("can_simulate_send")
    )
    return NodeExecutionResult(
        output={
            "selected_branch": "mock_send" if should_send else "draft_only",
            "requires_human": draft.get("requires_human", False),
        },
        state_updates={"customer_draft": draft},
        next_node="mock_send_customer_reply" if should_send else "finish_customer_reply",
    )


async def _customer_mock_send_input(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    draft = dict(context.state.get("customer_draft") or {})
    session_id = str(draft["session_id"])
    content = str(draft["reply"])
    payload = MockSendCustomerReplyInput(session_id=session_id, content=content)
    return NodeExecutionResult(
        tool_input=payload.model_dump(mode="json"),
        tool_target_type="customer_session",
        tool_target_id=session_id,
        before_snapshot={"session_id": session_id, "reply_status": "draft"},
        after_snapshot={"session_id": session_id, "reply_status": "mock_sent"},
        risk_warning="该操作只会向 Mock Shopee 会话写入一条模拟客服消息。",
    )


async def _finish_customer_reply(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    simulated_send = None
    last_output = dict(context.state.get("last_output") or {})
    if last_output.get("status") == "mock_sent":
        simulated_send = last_output
    return NodeExecutionResult(
        output={
            "draft": dict(context.state.get("customer_draft") or {}),
            "classification": dict(context.state.get("customer_classification") or {}),
            "evidence": dict(context.state.get("customer_evidence") or {}),
            "simulated_send": simulated_send,
        }
    )


async def _diagnostic_finish(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    return NodeExecutionResult(
        status=TaskStepStatus.SUCCEEDED,
        output={
            "status": "ok",
            "diagnostic": True,
            "message": context.workflow_input["message"],
        },
    )


async def _select_order_query_branch(
    context: TaskExecutionContext,
) -> NodeExecutionResult:
    selected = "get_order" if context.workflow_input.get("order_id") else "list_orders"
    return NodeExecutionResult(
        output={"selected_branch": selected},
        state_updates={"order_query_mode": "single" if selected == "get_order" else "list"},
        next_node=selected,
    )


async def _get_order_input(context: TaskExecutionContext) -> NodeExecutionResult:
    payload = GetOrderInput(order_id=str(context.workflow_input["order_id"]))
    return NodeExecutionResult(tool_input=payload.model_dump(mode="json"))


async def _list_orders_input(context: TaskExecutionContext) -> NodeExecutionResult:
    payload = ListOrdersInput(
        status=context.workflow_input.get("status"),
        shop_id=context.workflow_input.get("shop_id"),
        limit=int(context.workflow_input.get("limit", 20)),
    )
    return NodeExecutionResult(tool_input=payload.model_dump(mode="json"))


async def _finish_order_query(context: TaskExecutionContext) -> NodeExecutionResult:
    output = dict(context.state.get("last_output") or {})
    if context.state.get("order_query_mode") == "single":
        order = output.get("order")
        return NodeExecutionResult(
            output={
                "mode": "single",
                "order": order,
                "orders": [],
                "count": 1 if order else 0,
                "is_mock_data": bool(isinstance(order, dict) and order.get("is_mock_data", False)),
            }
        )
    return NodeExecutionResult(
        output={
            "mode": "list",
            "order": None,
            "orders": output.get("orders", []),
            "count": output.get("count", 0),
            "is_mock_data": output.get("is_mock_data", False),
        }
    )


def build_diagnostic_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="diagnostic",
        version="1.0.0",
        description="Run a deterministic no-LLM workflow runtime diagnostic.",
        task_type=TaskType.DIAGNOSTIC,
        input_schema=DiagnosticWorkflowInput,
        output_schema=DiagnosticWorkflowOutput,
        nodes=(
            NodeDefinition(
                name="diagnostic",
                node_type=WorkflowNodeType.FINISH,
                handler=_diagnostic_finish,
                timeout_seconds=min(
                    5,
                    settings.task_default_node_timeout_seconds,
                ),
            ),
        ),
        entry_node="diagnostic",
        max_steps=1,
        max_task_attempts=1,
    )


def build_system_health_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="system_health_check",
        version="1.0.0",
        description="Execute system_health through the unified ToolExecutor.",
        task_type=TaskType.DIAGNOSTIC,
        input_schema=SystemHealthWorkflowInput,
        output_schema=SystemHealthOutput,
        nodes=(
            NodeDefinition(
                name="system_health",
                node_type=WorkflowNodeType.TOOL,
                tool_name="system_health",
                timeout_seconds=min(
                    10,
                    settings.task_default_node_timeout_seconds,
                ),
            ),
        ),
        entry_node="system_health",
        max_steps=1,
        max_task_attempts=1,
    )


def build_selection_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="selection",
        version="1.0.0",
        description="Search bounded market candidates before deterministic opportunity scoring.",
        task_type=TaskType.SELECTION,
        input_schema=SelectionAnalysisRequest,
        output_schema=SelectionWorkflowOutput,
        nodes=(
            NodeDefinition(
                name="search_market_products",
                node_type=WorkflowNodeType.TOOL,
                tool_name="search_market_products",
                handler=_selection_search_input,
                next_node="select_selection_candidates",
                timeout_seconds=min(15, settings.task_max_node_timeout_seconds),
            ),
            NodeDefinition(
                name="select_selection_candidates",
                node_type=WorkflowNodeType.BRANCH,
                handler=_select_selection_candidate_branch,
                routes={
                    "score": "score_product_opportunity",
                    "no_data": "finish_selection_no_data",
                },
                timeout_seconds=min(5, settings.task_default_node_timeout_seconds),
            ),
            NodeDefinition(
                name="score_product_opportunity",
                node_type=WorkflowNodeType.TOOL,
                tool_name="score_product_opportunity",
                handler=_selection_score_input,
                timeout_seconds=min(
                    60,
                    settings.task_max_node_timeout_seconds,
                ),
            ),
            NodeDefinition(
                name="finish_selection_no_data",
                node_type=WorkflowNodeType.FINISH,
                handler=_finish_selection_no_data,
                timeout_seconds=min(5, settings.task_default_node_timeout_seconds),
            ),
        ),
        entry_node="search_market_products",
        max_steps=4,
        max_task_attempts=1,
    )


def build_review_analysis_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="review_analysis",
        version="1.0.0",
        description=(
            "Run the evidence-bound Review Analysis Service through the unified ToolExecutor."
        ),
        task_type=TaskType.REVIEW_ANALYSIS,
        input_schema=ReviewAnalysisCreateRequest,
        output_schema=AnalyzeProductReviewsOutput,
        nodes=(
            NodeDefinition(
                name="analyze_product_reviews",
                node_type=WorkflowNodeType.TOOL,
                tool_name="analyze_product_reviews",
                timeout_seconds=min(
                    60,
                    settings.task_max_node_timeout_seconds,
                ),
            ),
        ),
        entry_node="analyze_product_reviews",
        max_steps=1,
        max_task_attempts=1,
    )


def build_content_generation_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="content_generation",
        version="1.0.0",
        description=(
            "Generate localized content from database facts and verify final compliance "
            "through the unified ToolExecutor."
        ),
        task_type=TaskType.CONTENT_GENERATION,
        input_schema=ContentGenerateRequest,
        output_schema=ContentWorkflowOutput,
        nodes=(
            NodeDefinition(
                name="generate_localized_listing",
                node_type=WorkflowNodeType.TOOL,
                tool_name="generate_localized_listing",
                next_node="check_listing_compliance",
                timeout_seconds=min(90, settings.task_max_node_timeout_seconds),
            ),
            NodeDefinition(
                name="check_listing_compliance",
                node_type=WorkflowNodeType.TOOL,
                tool_name="check_listing_compliance",
                handler=_content_compliance_input,
                next_node="validate_content_quality",
                timeout_seconds=min(15, settings.task_max_node_timeout_seconds),
            ),
            NodeDefinition(
                name="validate_content_quality",
                node_type=WorkflowNodeType.BRANCH,
                handler=_validate_content_quality,
                routes={"passed": "finish_content_generation"},
                timeout_seconds=min(5, settings.task_default_node_timeout_seconds),
            ),
            NodeDefinition(
                name="finish_content_generation",
                node_type=WorkflowNodeType.FINISH,
                handler=_finish_content_generation,
                timeout_seconds=min(5, settings.task_default_node_timeout_seconds),
            ),
        ),
        entry_node="generate_localized_listing",
        max_steps=4,
        max_task_attempts=1,
    )


def build_knowledge_query_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="knowledge_query",
        version="1.0.0",
        description="Search the existing knowledge base through the unified ToolExecutor.",
        task_type=TaskType.KNOWLEDGE_INGESTION,
        input_schema=SearchKnowledgeInput,
        output_schema=SearchKnowledgeOutput,
        nodes=(
            NodeDefinition(
                name="search_knowledge",
                node_type=WorkflowNodeType.TOOL,
                tool_name="search_knowledge",
                timeout_seconds=min(90, settings.task_max_node_timeout_seconds),
            ),
        ),
        entry_node="search_knowledge",
        max_steps=1,
        max_task_attempts=1,
    )


def build_customer_service_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="customer_service_reply",
        version="1.0.0",
        description=(
            "Read a customer conversation, record a risk branch, ground the draft in "
            "commerce or knowledge evidence, and optionally request Mock-send confirmation."
        ),
        task_type=TaskType.CUSTOMER_SERVICE,
        input_schema=CustomerServiceWorkflowInput,
        output_schema=CustomerServiceWorkflowOutput,
        nodes=(
            NodeDefinition(
                name="get_customer_conversation",
                node_type=WorkflowNodeType.TOOL,
                tool_name="get_customer_conversation",
                handler=_customer_context_input,
                next_node="classify_customer_request",
            ),
            NodeDefinition(
                name="classify_customer_request",
                node_type=WorkflowNodeType.TOOL,
                tool_name="classify_customer_request",
                handler=_customer_classification_input,
                next_node="select_customer_branch",
            ),
            NodeDefinition(
                name="select_customer_branch",
                node_type=WorkflowNodeType.BRANCH,
                handler=_select_customer_branch,
                routes={
                    "human": "record_customer_handoff",
                    "policy": "search_customer_knowledge",
                    "order": "get_customer_order",
                    "logistics": "get_customer_logistics",
                    "product": "get_customer_product",
                },
            ),
            NodeDefinition(
                name="record_customer_handoff",
                node_type=WorkflowNodeType.ACTION,
                handler=_record_customer_handoff,
                next_node="draft_customer_reply",
            ),
            NodeDefinition(
                name="search_customer_knowledge",
                node_type=WorkflowNodeType.TOOL,
                tool_name="search_knowledge",
                handler=_customer_knowledge_input,
                next_node="draft_customer_reply",
            ),
            NodeDefinition(
                name="get_customer_order",
                node_type=WorkflowNodeType.TOOL,
                tool_name="get_order",
                handler=_customer_order_input,
                next_node="draft_customer_reply",
            ),
            NodeDefinition(
                name="get_customer_logistics",
                node_type=WorkflowNodeType.TOOL,
                tool_name="get_order_logistics",
                handler=_customer_logistics_input,
                next_node="draft_customer_reply",
            ),
            NodeDefinition(
                name="get_customer_product",
                node_type=WorkflowNodeType.TOOL,
                tool_name="get_product",
                handler=_customer_product_input,
                next_node="draft_customer_reply",
            ),
            NodeDefinition(
                name="draft_customer_reply",
                node_type=WorkflowNodeType.TOOL,
                tool_name="draft_customer_reply",
                handler=_customer_draft_input,
                next_node="select_customer_send",
            ),
            NodeDefinition(
                name="select_customer_send",
                node_type=WorkflowNodeType.BRANCH,
                handler=_select_customer_send_branch,
                routes={
                    "send": "mock_send_customer_reply",
                    "draft": "finish_customer_reply",
                },
            ),
            NodeDefinition(
                name="mock_send_customer_reply",
                node_type=WorkflowNodeType.TOOL,
                tool_name="mock_send_customer_reply",
                handler=_customer_mock_send_input,
                next_node="finish_customer_reply",
            ),
            NodeDefinition(
                name="finish_customer_reply",
                node_type=WorkflowNodeType.FINISH,
                handler=_finish_customer_reply,
            ),
        ),
        entry_node="get_customer_conversation",
        max_steps=8,
        max_task_attempts=1,
    )


def build_product_improvement_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="product_improvement",
        version="1.0.0",
        description=(
            "Generate an evidence-bound product improvement report through the unified "
            "ToolExecutor."
        ),
        task_type=TaskType.PRODUCT_IMPROVEMENT,
        input_schema=ProductImprovementWorkflowInput,
        output_schema=ImprovementToolOutput,
        nodes=(
            NodeDefinition(
                name="select_improvement_source",
                node_type=WorkflowNodeType.BRANCH,
                handler=_select_improvement_source,
                routes={
                    "analysis": "generate_product_improvement_plan",
                    "product": "analyze_reviews_for_improvement",
                },
            ),
            NodeDefinition(
                name="analyze_reviews_for_improvement",
                node_type=WorkflowNodeType.TOOL,
                tool_name="analyze_product_reviews",
                handler=_improvement_review_input,
                next_node="generate_product_improvement_plan",
                timeout_seconds=min(60, settings.task_max_node_timeout_seconds),
            ),
            NodeDefinition(
                name="generate_product_improvement_plan",
                node_type=WorkflowNodeType.TOOL,
                tool_name="generate_product_improvement_plan",
                handler=_improvement_generate_input,
                timeout_seconds=min(
                    30,
                    settings.task_max_node_timeout_seconds,
                ),
            ),
        ),
        entry_node="select_improvement_source",
        max_steps=3,
        max_task_attempts=1,
    )


def build_low_stock_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="low_stock_check",
        version="1.0.0",
        description="Read bounded low-stock inventory through the unified ToolExecutor.",
        task_type=TaskType.PLATFORM_OPERATION,
        input_schema=ListLowStockInput,
        output_schema=ListInventoryOutput,
        nodes=(
            NodeDefinition(
                name="list_low_stock",
                node_type=WorkflowNodeType.TOOL,
                tool_name="list_low_stock",
                timeout_seconds=min(10, settings.task_max_node_timeout_seconds),
            ),
        ),
        entry_node="list_low_stock",
        max_steps=1,
        max_task_attempts=1,
    )


def build_order_query_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="order_query",
        version="1.0.0",
        description=(
            "Branch between one-order and bounded order-list reads through the unified "
            "ToolExecutor."
        ),
        task_type=TaskType.PLATFORM_OPERATION,
        input_schema=OrderQueryWorkflowInput,
        output_schema=OrderQueryWorkflowOutput,
        nodes=(
            NodeDefinition(
                name="select_order_query",
                node_type=WorkflowNodeType.BRANCH,
                handler=_select_order_query_branch,
                routes={"single": "get_order", "list": "list_orders"},
                timeout_seconds=min(5, settings.task_default_node_timeout_seconds),
            ),
            NodeDefinition(
                name="get_order",
                node_type=WorkflowNodeType.TOOL,
                tool_name="get_order",
                handler=_get_order_input,
                next_node="finish_order_query",
                timeout_seconds=min(10, settings.task_max_node_timeout_seconds),
            ),
            NodeDefinition(
                name="list_orders",
                node_type=WorkflowNodeType.TOOL,
                tool_name="list_orders",
                handler=_list_orders_input,
                next_node="finish_order_query",
                timeout_seconds=min(10, settings.task_max_node_timeout_seconds),
            ),
            NodeDefinition(
                name="finish_order_query",
                node_type=WorkflowNodeType.FINISH,
                handler=_finish_order_query,
                timeout_seconds=min(5, settings.task_default_node_timeout_seconds),
            ),
        ),
        entry_node="select_order_query",
        max_steps=3,
        max_task_attempts=1,
    )


def build_logistics_query_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="logistics_query",
        version="1.0.0",
        description="Read one order's logistics through the unified ToolExecutor.",
        task_type=TaskType.PLATFORM_OPERATION,
        input_schema=GetOrderLogisticsInput,
        output_schema=GetOrderLogisticsOutput,
        nodes=(
            NodeDefinition(
                name="get_order_logistics",
                node_type=WorkflowNodeType.TOOL,
                tool_name="get_order_logistics",
                timeout_seconds=min(10, settings.task_max_node_timeout_seconds),
            ),
        ),
        entry_node="get_order_logistics",
        max_steps=1,
        max_task_attempts=1,
    )


def build_replenishment_definition(settings: Settings) -> WorkflowDefinition:
    # 当前是单工具节点工作流。PPT中的读取、聚合、计算、分级和生成依据，
    # 是该节点内部的业务阶段，不代表已实现七个独立工作流节点。
    return WorkflowDefinition(
        name="inventory_replenishment",
        version="1.0.0",
        description=(
            "Analyze inventory health and recent SKU demand through a deterministic read tool."
        ),
        task_type=TaskType.REPLENISHMENT,
        input_schema=ReplenishmentAnalysisRequest,
        output_schema=ReplenishmentAnalysisOutput,
        nodes=(
            NodeDefinition(
                name="analyze_inventory_replenishment",
                node_type=WorkflowNodeType.TOOL,
                tool_name="analyze_inventory_replenishment",
                timeout_seconds=min(30, settings.task_max_node_timeout_seconds),
            ),
        ),
        entry_node="analyze_inventory_replenishment",
        max_steps=1,
        max_task_attempts=1,
    )


def build_workflow_registry(settings: Settings) -> WorkflowRegistry:
    registry = WorkflowRegistry(settings)
    registry.register(build_diagnostic_definition(settings))
    registry.register(build_system_health_definition(settings))
    registry.register(build_selection_definition(settings))
    registry.register(build_review_analysis_definition(settings))
    registry.register(build_content_generation_definition(settings))
    registry.register(build_knowledge_query_definition(settings))
    registry.register(build_customer_service_definition(settings))
    registry.register(build_product_improvement_definition(settings))
    registry.register(build_low_stock_definition(settings))
    registry.register(build_order_query_definition(settings))
    registry.register(build_logistics_query_definition(settings))
    registry.register(build_replenishment_definition(settings))
    return registry
