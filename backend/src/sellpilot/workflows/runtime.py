from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sellpilot.core.config import Settings
from sellpilot.core.enums import TaskStepStatus, TaskType, WorkflowNodeType
from sellpilot.schemas.commerce import OrderResponse
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
    ListInventoryOutput,
    ListLowStockInput,
    ListOrdersInput,
)
from sellpilot.tools.product_improvement import GenerateImprovementInput, ImprovementToolOutput
from sellpilot.tools.review_analysis import AnalyzeProductReviewsOutput
from sellpilot.tools.selection import ScoreProductOpportunityOutput
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
        description=(
            "Adapt the existing deterministic Selection Service through its registered tool."
        ),
        task_type=TaskType.SELECTION,
        input_schema=SelectionAnalysisRequest,
        output_schema=ScoreProductOpportunityOutput,
        nodes=(
            NodeDefinition(
                name="score_product_opportunity",
                node_type=WorkflowNodeType.TOOL,
                tool_name="score_product_opportunity",
                timeout_seconds=min(
                    60,
                    settings.task_max_node_timeout_seconds,
                ),
            ),
        ),
        entry_node="score_product_opportunity",
        max_steps=1,
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


def build_product_improvement_definition(settings: Settings) -> WorkflowDefinition:
    return WorkflowDefinition(
        name="product_improvement",
        version="1.0.0",
        description=(
            "Generate an evidence-bound product improvement report through the unified "
            "ToolExecutor."
        ),
        task_type=TaskType.PRODUCT_IMPROVEMENT,
        input_schema=GenerateImprovementInput,
        output_schema=ImprovementToolOutput,
        nodes=(
            NodeDefinition(
                name="generate_product_improvement_plan",
                node_type=WorkflowNodeType.TOOL,
                tool_name="generate_product_improvement_plan",
                timeout_seconds=min(
                    30,
                    settings.task_max_node_timeout_seconds,
                ),
            ),
        ),
        entry_node="generate_product_improvement_plan",
        max_steps=1,
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
    registry.register(build_product_improvement_definition(settings))
    registry.register(build_low_stock_definition(settings))
    registry.register(build_order_query_definition(settings))
    registry.register(build_logistics_query_definition(settings))
    registry.register(build_replenishment_definition(settings))
    return registry
