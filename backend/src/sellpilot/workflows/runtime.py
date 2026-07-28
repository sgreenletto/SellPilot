from pydantic import BaseModel, ConfigDict, Field

from sellpilot.core.config import Settings
from sellpilot.core.enums import TaskStepStatus, TaskType, WorkflowNodeType
from sellpilot.schemas.selection import SelectionAnalysisRequest
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


def build_workflow_registry(settings: Settings) -> WorkflowRegistry:
    registry = WorkflowRegistry(settings)
    registry.register(build_diagnostic_definition(settings))
    registry.register(build_system_health_definition(settings))
    registry.register(build_selection_definition(settings))
    return registry
