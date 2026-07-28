from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from sellpilot.core.enums import TaskStatus, TaskStepStatus, TaskType, WorkflowNodeType

WorkflowName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
    ),
]
WorkflowVersion = Annotated[
    str,
    StringConstraints(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"),
]


class TaskExecutionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    user_id: UUID
    request_id: str = Field(min_length=36, max_length=36)
    workflow_name: str
    workflow_version: str
    workflow_input: dict[str, JsonValue]
    state: dict[str, JsonValue] = Field(default_factory=dict)
    current_node: str
    current_step_id: UUID | None = None
    task_attempt: int = Field(ge=1)
    metadata: dict[str, str | int | bool | None] = Field(default_factory=dict)

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        return str(UUID(value))

    @field_validator("metadata")
    @classmethod
    def validate_metadata(
        cls, value: dict[str, str | int | bool | None]
    ) -> dict[str, str | int | bool | None]:
        if len(value) > 20:
            raise ValueError("metadata supports at most 20 entries")
        return value


class NodeExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TaskStepStatus = TaskStepStatus.SUCCEEDED
    output: dict[str, JsonValue] = Field(default_factory=dict)
    state_updates: dict[str, JsonValue] = Field(default_factory=dict)
    next_node: str | None = None
    tool_input: dict[str, JsonValue] | None = None
    tool_target_type: str = "workflow"
    tool_target_id: str | None = None
    before_snapshot: dict[str, JsonValue] | None = None
    after_snapshot: dict[str, JsonValue] | None = None
    risk_warning: str | None = None
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=255)
    confirmation_required: bool = False
    confirmation_id: UUID | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False


NodeHandler = Callable[
    [TaskExecutionContext],
    NodeExecutionResult | Awaitable[NodeExecutionResult],
]


class NodeDefinition(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
    )

    name: WorkflowName
    node_type: WorkflowNodeType
    handler: NodeHandler | None = Field(default=None, exclude=True)
    tool_name: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")
    next_node: str | None = None
    routes: dict[str, str] = Field(default_factory=dict)
    max_attempts: int = Field(default=1, ge=1, le=5)
    timeout_seconds: float | None = Field(default=None, gt=0)
    optional: bool = False
    resumable: bool = True
    loop_limit: int | None = Field(default=None, ge=1, le=100)

    @model_validator(mode="after")
    def validate_node_contract(self) -> "NodeDefinition":
        if self.node_type is WorkflowNodeType.TOOL and not self.tool_name:
            raise ValueError("tool nodes require tool_name")
        if self.node_type is WorkflowNodeType.ACTION and self.handler is None:
            raise ValueError("action nodes require a server-side handler")
        if self.node_type in {WorkflowNodeType.BRANCH, WorkflowNodeType.LOOP}:
            if self.handler is None:
                raise ValueError("branch and loop nodes require a server-side handler")
            if not self.routes:
                raise ValueError("branch and loop nodes require finite routes")
        if self.node_type is WorkflowNodeType.LOOP and self.loop_limit is None:
            raise ValueError("loop nodes require loop_limit")
        if self.node_type is WorkflowNodeType.FINISH and self.next_node is not None:
            raise ValueError("finish nodes cannot define next_node")
        if (
            self.node_type not in {WorkflowNodeType.FINISH, WorkflowNodeType.TOOL}
            and self.next_node is None
            and not self.routes
        ):
            raise ValueError("non-finish nodes require a finite outgoing edge")
        return self


class WorkflowDefinition(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
    )

    name: WorkflowName
    version: WorkflowVersion
    description: str = Field(min_length=1, max_length=500)
    task_type: TaskType
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    nodes: tuple[NodeDefinition, ...] = Field(min_length=1, max_length=200)
    entry_node: str
    enabled: bool = True
    resumable: bool = True
    max_steps: int = Field(default=50, ge=1, le=200)
    max_task_attempts: int = Field(default=3, ge=1, le=5)

    @field_validator("input_schema", "output_schema")
    @classmethod
    def validate_schema(cls, value: type[BaseModel]) -> type[BaseModel]:
        if not isinstance(value, type) or not issubclass(value, BaseModel):
            raise TypeError("workflow schemas must be Pydantic BaseModel classes")
        return value

    @model_validator(mode="after")
    def validate_graph(self) -> "WorkflowDefinition":
        names = [node.name for node in self.nodes]
        if len(names) != len(set(names)):
            raise ValueError("workflow node names must be unique")
        known = set(names)
        if self.entry_node not in known:
            raise ValueError("entry_node must reference an existing node")
        for node in self.nodes:
            references = ([node.next_node] if node.next_node else []) + list(node.routes.values())
            missing = sorted(reference for reference in references if reference not in known)
            if missing:
                raise ValueError(
                    f"node '{node.name}' references unknown nodes: {', '.join(missing)}"
                )
        if not any(
            node.node_type is WorkflowNodeType.FINISH
            or (node.node_type is WorkflowNodeType.TOOL and node.next_node is None)
            for node in self.nodes
        ):
            raise ValueError("workflow requires a finite terminal node")
        return self

    @property
    def node_map(self) -> dict[str, NodeDefinition]:
        return {node.name: node for node in self.nodes}


class WorkflowMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    description: str
    task_type: TaskType
    enabled: bool
    resumable: bool
    max_steps: int
    max_task_attempts: int


class TaskExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    workflow_name: str
    workflow_version: str
    status: TaskStatus
    current_node: str | None
    current_step_id: UUID | None = None
    confirmation_required: bool = False
    confirmation_id: UUID | None = None
    result: dict[str, JsonValue] | None = None
    error_code: str | None = None
    error_message: str | None = None
    task_attempt: int = Field(ge=0)
    request_id: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
