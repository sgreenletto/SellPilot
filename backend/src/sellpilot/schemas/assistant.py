from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints

from sellpilot.core.enums import TaskStatus, ToolRiskLevel
from sellpilot.schemas.common import ApiDateTime


class AssistantAvailability(StrEnum):
    AVAILABLE = "available"
    CONTRACT_ONLY = "contract_only"
    UNAVAILABLE = "unavailable"


class AssistantIntent(StrEnum):
    SELECTION_ANALYSIS = "selection_analysis"
    REVIEW_ANALYSIS = "review_analysis"
    PRODUCT_IMPROVEMENT = "product_improvement"
    CONTENT_GENERATION = "content_generation"
    INVENTORY_REPLENISHMENT = "inventory_replenishment"
    LOW_STOCK_CHECK = "low_stock_check"
    ORDER_QUERY = "order_query"
    LOGISTICS_QUERY = "logistics_query"
    KNOWLEDGE_QUERY = "knowledge_query"
    CUSTOMER_SERVICE_REPLY = "customer_service_reply"
    UNKNOWN = "unknown"


class AssistantCapabilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_key: str
    display_name: str
    intent: AssistantIntent
    workflow_name: str | None
    workflow_version: str | None
    required_parameters: list[str]
    optional_parameters: list[str]
    tool_names: list[str]
    risk_level: ToolRiskLevel
    requires_confirmation: bool
    availability: AssistantAvailability
    unavailable_reason: str | None
    example_message: str
    target_path: str


class AssistantPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
    ]


AssistantExecutionMode = Literal["create_only", "create_and_run"]


class AssistantTaskRequest(AssistantPlanRequest):
    execution_mode: AssistantExecutionMode


class AssistantWorkflowReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str


class AssistantPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int = Field(ge=1)
    kind: Literal["workflow", "tool", "capability"]
    name: str
    summary: str


class AssistantPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detected_intent: AssistantIntent
    extracted_parameters: dict[str, JsonValue]
    missing_parameters: list[str]
    selected_capability: str | None
    selected_workflow: AssistantWorkflowReference | None
    tool_names: list[str]
    steps: list[AssistantPlanStep]
    risk_summary: str
    requires_confirmation: bool
    availability: AssistantAvailability
    unavailable_reason: str | None
    can_execute: bool
    target_path: str | None
    mock_mode: bool = True
    mock_notice: str


class AssistantTaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detected_intent: AssistantIntent
    selected_capability: str
    workflow_name: str
    workflow_version: str
    plan: AssistantPlanResponse
    task_id: UUID
    task_status: TaskStatus
    execution_mode: AssistantExecutionMode
    confirmation_required: bool
    confirmation_id: UUID | None = None
    duplicate: bool = False
    created_at: ApiDateTime
