from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.enums import RiskLevel

SENSITIVE_KEYS = {"password", "token", "authorization", "api_key", "jwt", "secret"}


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if any(sensitive in str(key).lower() for sensitive in SENSITIVE_KEYS)
            else sanitize_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]
    return value


class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: UUID | None = None
    task_id: UUID | None = None
    confirmation_granted: bool = False
    session: AsyncSession | None = Field(default=None, exclude=True)


class ToolResult(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    duration_ms: int


ToolHandler = Callable[[BaseModel, ToolContext], Awaitable[BaseModel | dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    risk_level: RiskLevel
    requires_confirmation: bool
    timeout_seconds: float
    handler: ToolHandler
