import asyncio
from time import perf_counter

from pydantic import ValidationError

from sellpilot.core.enums import RiskLevel, ToolCallStatus
from sellpilot.core.exceptions import (
    AppException,
    DuplicateOperationError,
    ResourceNotFoundError,
)
from sellpilot.db.models.tool_call import ToolCall
from sellpilot.tools.contracts import (
    ToolContext,
    ToolDefinition,
    ToolResult,
    sanitize_payload,
)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise DuplicateOperationError(f"Tool '{definition.name}' is already registered")
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ResourceNotFoundError(f"Tool '{name}' is not registered") from exc

    def list(self) -> list[ToolDefinition]:
        return [self._tools[name] for name in sorted(self._tools)]

    async def invoke(
        self, name: str, payload: dict[str, object], context: ToolContext
    ) -> ToolResult:
        definition = self.get(name)
        started = perf_counter()
        status = ToolCallStatus.FAILED

        try:
            validated_input = definition.input_schema.model_validate(payload)
            if (
                definition.risk_level in {RiskLevel.WRITE, RiskLevel.HIGH_RISK}
                or definition.requires_confirmation
            ) and not context.confirmation_granted:
                status = ToolCallStatus.BLOCKED
                result = ToolResult(
                    success=False,
                    error_code="TOOL_CONFIRMATION_REQUIRED",
                    error_message="Tool execution requires a confirmed task",
                    duration_ms=self._duration_ms(started),
                )
            else:
                raw_output = await asyncio.wait_for(
                    definition.handler(validated_input, context),
                    timeout=definition.timeout_seconds,
                )
                validated_output = definition.output_schema.model_validate(raw_output)
                status = ToolCallStatus.SUCCEEDED
                result = ToolResult(
                    success=True,
                    data=validated_output.model_dump(mode="json"),
                    duration_ms=self._duration_ms(started),
                )
        except TimeoutError:
            status = ToolCallStatus.TIMED_OUT
            result = ToolResult(
                success=False,
                error_code="TOOL_TIMEOUT",
                error_message=f"Tool '{name}' exceeded its timeout",
                duration_ms=self._duration_ms(started),
            )
        except ValidationError:
            result = ToolResult(
                success=False,
                error_code="TOOL_SCHEMA_VALIDATION_FAILED",
                error_message="Tool input or output failed schema validation",
                duration_ms=self._duration_ms(started),
            )
        except AppException as exc:
            result = ToolResult(
                success=False,
                error_code=exc.code,
                error_message=exc.message,
                duration_ms=self._duration_ms(started),
            )
        except Exception:
            result = ToolResult(
                success=False,
                error_code="TOOL_FAILED",
                error_message=f"Tool '{name}' failed",
                duration_ms=self._duration_ms(started),
            )

        if context.session is not None:
            context.session.add(
                ToolCall(
                    task_id=context.task_id,
                    tool_name=definition.name,
                    risk_level=definition.risk_level,
                    status=status,
                    input_summary=sanitize_payload(payload),
                    output_summary=sanitize_payload(result.data),
                    duration_ms=result.duration_ms,
                    error_code=result.error_code,
                    error_message=result.error_message,
                )
            )
            await context.session.flush()
        return result

    @staticmethod
    def _duration_ms(started: float) -> int:
        return max(0, int((perf_counter() - started) * 1000))
