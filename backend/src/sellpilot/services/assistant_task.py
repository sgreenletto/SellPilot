from __future__ import annotations

import json
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.core.enums import TaskStatus
from sellpilot.core.exceptions import IdempotencyConflictError, ParameterError, StateConflictError
from sellpilot.core.logging import redact_sensitive
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.schemas.assistant import (
    AssistantAvailability,
    AssistantExecutionMode,
    AssistantIntent,
    AssistantTaskResponse,
)
from sellpilot.services.assistant import AssistantCapabilityRegistry, AssistantPlanService
from sellpilot.services.task import TaskService
from sellpilot.tools.registry import ToolRegistry
from sellpilot.workflows.registry import WorkflowRegistry
from sellpilot.workflows.runner import TaskRunner


class AssistantTaskService:
    """Create and optionally run Assistant plans through the existing task runtime."""

    def __init__(
        self,
        *,
        capabilities: AssistantCapabilityRegistry,
        workflows: WorkflowRegistry,
        tools: ToolRegistry,
        session: AsyncSession,
        settings: Settings,
    ) -> None:
        self.capabilities = capabilities
        self.workflows = workflows
        self.tools = tools
        self.session = session
        self.settings = settings
        self.tasks = TaskService(session, settings)

    async def create(
        self,
        *,
        message: str,
        execution_mode: AssistantExecutionMode,
        user_id: UUID,
        request_id: str,
    ) -> AssistantTaskResponse:
        plan = AssistantPlanService(self.capabilities).plan(message)
        if plan.detected_intent is AssistantIntent.UNKNOWN or plan.selected_capability is None:
            raise ParameterError("Assistant intent is not executable")
        if plan.missing_parameters:
            raise ParameterError(
                "Assistant task is missing required parameters",
                details={"missing_parameters": plan.missing_parameters},
            )
        if plan.availability is not AssistantAvailability.AVAILABLE:
            raise StateConflictError(
                plan.unavailable_reason or "Assistant capability is not available"
            )
        if not plan.can_execute or plan.selected_workflow is None:
            raise StateConflictError("Assistant capability has no executable workflow")

        capability = self.capabilities.get_by_intent(plan.detected_intent)
        if capability is None or capability.capability_key != plan.selected_capability:
            raise StateConflictError("Assistant capability mapping changed during planning")
        definition = self.workflows.get(
            plan.selected_workflow.name,
            required_version=plan.selected_workflow.version,
        )
        workflow_input = dict(plan.extracted_parameters)
        if plan.detected_intent is AssistantIntent.REVIEW_ANALYSIS:
            workflow_input["idempotency_key"] = f"assistant-{request_id}"
        try:
            trusted_input = definition.input_schema.model_validate(workflow_input).model_dump(
                mode="json"
            )
        except ValidationError as exc:
            raise ParameterError("Assistant workflow input is invalid") from exc

        user_input_summary = self._safe_user_input(message)
        await self._lock_request_scope(user_id=user_id, request_id=request_id)
        existing = await self.tasks.tasks.find_owned_by_request_id(
            user_id=user_id,
            request_id=request_id,
        )
        duplicate = existing is not None
        if existing is not None:
            self._validate_idempotent_match(
                existing,
                workflow_name=definition.name,
                workflow_version=definition.version,
                workflow_input=trusted_input,
                user_input_summary=user_input_summary,
            )
            task = existing
        else:
            task = await self.tasks.create_workflow_task(
                definition,
                workflow_input=trusted_input,
                created_by=user_id,
                request_id=request_id,
                user_input_summary=user_input_summary,
                creation_context={
                    "source": "assistant",
                    "intent": plan.detected_intent.value,
                    "capability": capability.capability_key,
                    "workflow_name": definition.name,
                    "workflow_version": definition.version,
                },
            )
        await self.session.commit()

        confirmation_required = plan.requires_confirmation
        confirmation_id = None
        if execution_mode == "create_and_run" and TaskStatus(task.status) is TaskStatus.PENDING:
            execution = await TaskRunner(
                self.workflows,
                self.tools,
                self.session,
                self.settings,
            ).run(
                task.id,
                user_id=user_id,
                request_id=request_id,
            )
            confirmation_required = execution.confirmation_required
            confirmation_id = execution.confirmation_id
            await self.session.refresh(task)

        return AssistantTaskResponse(
            detected_intent=plan.detected_intent,
            selected_capability=capability.capability_key,
            workflow_name=definition.name,
            workflow_version=definition.version,
            plan=plan,
            task_id=task.id,
            task_status=TaskStatus(task.status),
            execution_mode=execution_mode,
            confirmation_required=confirmation_required,
            confirmation_id=confirmation_id,
            duplicate=duplicate,
            created_at=task.created_at,
        )

    async def list_recent(self, *, user_id: UUID, limit: int) -> list[AgentTask]:
        return await self.tasks.tasks.list_recent_assistant_tasks(
            user_id=user_id,
            limit=limit,
        )

    async def _lock_request_scope(self, *, user_id: UUID, request_id: str) -> None:
        bind = self.session.get_bind()
        if bind.dialect.name != "postgresql":
            return
        scope = f"assistant-task:{user_id}:{request_id}"
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
            {"scope": scope},
        )

    @staticmethod
    def _safe_user_input(message: str) -> str:
        summary = redact_sensitive(message.strip())[:1000]
        return json.dumps(
            {"source": "assistant", "message_summary": summary},
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _validate_idempotent_match(
        existing: AgentTask,
        *,
        workflow_name: str,
        workflow_version: str,
        workflow_input: dict[str, object],
        user_input_summary: str,
    ) -> None:
        if (
            existing.workflow_name != workflow_name
            or existing.workflow_version != workflow_version
            or existing.workflow_input != workflow_input
            or existing.user_input != user_input_summary
        ):
            raise IdempotencyConflictError(
                "X-Request-ID is already associated with another Assistant task"
            )
