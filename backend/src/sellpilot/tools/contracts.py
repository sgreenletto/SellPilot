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

from sellpilot.core.enums import ToolCallerType, ToolCallStatus, ToolRiskLevel
from sellpilot.tools.sanitization import contains_sensitive_values

ToolName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
    ),
]
ToolVersion = Annotated[
    str,
    StringConstraints(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"),
]


class RetryPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_attempts: int = Field(ge=1, le=3)
    initial_delay_ms: int = Field(ge=0, le=60_000)
    max_delay_ms: int = Field(ge=0, le=60_000)
    backoff_multiplier: float = Field(ge=1, le=10)
    retryable_error_codes: frozenset[str] = Field(default_factory=frozenset)

    @model_validator(mode="after")
    def validate_delay_range(self) -> "RetryPolicy":
        if self.initial_delay_ms > self.max_delay_ms:
            raise ValueError("initial_delay_ms must not exceed max_delay_ms")
        return self


class ToolExecutionContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str = Field(min_length=36, max_length=36)
    user_id: UUID | None = None
    task_id: UUID | None = None
    task_step_id: UUID | None = None
    confirmation_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=255)
    caller_type: ToolCallerType
    caller_name: str = Field(min_length=1, max_length=100)
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
        for key, item in value.items():
            if len(key) > 64:
                raise ValueError("metadata keys must not exceed 64 characters")
            if isinstance(item, str) and len(item) > 500:
                raise ValueError("metadata string values must not exceed 500 characters")
        if contains_sensitive_values(value):
            raise ValueError("metadata must not contain sensitive fields")
        return value


class ToolExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: UUID
    tool_name: str
    tool_version: str
    status: ToolCallStatus
    data: dict[str, JsonValue] | None = None
    error_code: str | None = None
    error_message: str | None = None
    confirmation_required: bool = False
    confirmation_id: UUID | None = None
    attempt_count: int = Field(ge=0)
    duration_ms: int = Field(ge=0)
    request_id: str
    task_id: UUID | None = None
    started_at: datetime
    completed_at: datetime | None = None


class ToolPublicMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    description: str
    risk_level: ToolRiskLevel
    timeout_seconds: float
    enabled: bool
    expose_to_mcp: bool
    confirmation_required: bool
    input_json_schema: dict[str, JsonValue]
    output_json_schema: dict[str, JsonValue]


ToolHandlerResult = BaseModel | dict[str, JsonValue]
ToolHandler = Callable[
    [BaseModel, ToolExecutionContext],
    ToolHandlerResult | Awaitable[ToolHandlerResult],
]


class ToolDefinition(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
    )

    name: ToolName
    version: ToolVersion
    description: str = Field(min_length=1, max_length=500)
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    risk_level: ToolRiskLevel
    timeout_seconds: float | None = Field(default=None, gt=0)
    retry_policy: RetryPolicy
    idempotent: bool
    expose_to_mcp: bool
    enabled: bool = True
    sensitive_input_fields: frozenset[str] = Field(default_factory=frozenset)
    sensitive_output_fields: frozenset[str] = Field(default_factory=frozenset)
    allow_high_risk_mcp: bool = False
    handler: ToolHandler = Field(exclude=True)

    @field_validator("input_schema", "output_schema")
    @classmethod
    def validate_schema(cls, value: type[BaseModel]) -> type[BaseModel]:
        if not isinstance(value, type) or not issubclass(value, BaseModel):
            raise TypeError("tool schemas must be Pydantic BaseModel classes")
        return value

    @model_validator(mode="after")
    def validate_risk_policy(self) -> "ToolDefinition":
        if self.risk_level is not ToolRiskLevel.READ and self.retry_policy.max_attempts != 1:
            raise ValueError("write and high-risk tools must use exactly one attempt")
        if (
            self.risk_level is ToolRiskLevel.HIGH_RISK
            and self.expose_to_mcp
            and not self.allow_high_risk_mcp
        ):
            raise ValueError("high-risk MCP exposure requires explicit allow_high_risk_mcp")
        return self

    @property
    def confirmation_required(self) -> bool:
        return self.risk_level is not ToolRiskLevel.READ
