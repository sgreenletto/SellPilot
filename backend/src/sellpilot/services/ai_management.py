import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import BACKEND_ROOT, Settings
from sellpilot.core.enums import OperationStatus, ToolRiskLevel
from sellpilot.core.exceptions import (
    IdempotencyConflictError,
    ParameterError,
    ResourceNotFoundError,
)
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.db.models.model_management import PromptVersion
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.evaluation.member3 import evaluate_member3
from sellpilot.repositories.model_management import ModelInvocationRepository, PromptRepository
from sellpilot.repositories.operation_log import OperationLogRepository
from sellpilot.schemas.ai_management import (
    EvaluationCaseSummary,
    MemberThreeEvaluationSummary,
    ModelInvocationSummary,
    ModelRuntimeSummary,
    PromptStatusChangeRequest,
    PromptTemplateSummary,
    PromptVersionChangeRequest,
    PromptVersionSummary,
)
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.services.task import TaskService
from sellpilot.tools.sanitization import contains_sensitive_values

CREATE_PROMPT_VERSION = "create_prompt_version"
SET_PROMPT_STATUS = "set_prompt_status"


class AIManagementService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.prompts = PromptRepository(session)
        self.invocations = ModelInvocationRepository(session)
        self.tasks = TaskService(session, settings)
        self.logs = OperationLogRepository(session)
        self.settings = settings

    async def list_prompts(self) -> list[PromptTemplateSummary]:
        templates, _ = await self.prompts.list_templates(1, 100)
        result: list[PromptTemplateSummary] = []
        for template in templates:
            latest = await self.prompts.get_latest_version(template.id)
            _, count = await self.prompts.list_versions(template.id, 1, 1)
            result.append(
                PromptTemplateSummary(
                    id=template.id,
                    key=template.key,
                    name=template.name,
                    purpose=template.purpose,
                    task_type=template.task_type,
                    language=template.language,
                    status=template.status,
                    latest_version=self._prompt_version(latest) if latest else None,
                    version_count=count,
                    created_at=template.created_at,
                    updated_at=template.updated_at,
                )
            )
        return result

    async def list_prompt_versions(self, template_id) -> list[PromptVersionSummary]:
        if await self.prompts.get_template(template_id) is None:
            raise ResourceNotFoundError("Prompt template not found")
        rows, _ = await self.prompts.list_versions(template_id, 1, 100)
        return [self._prompt_version(row) for row in rows]

    async def request_version_change(
        self,
        template_id: UUID,
        payload: PromptVersionChangeRequest,
        user_id: UUID,
    ) -> ConfirmationTask:
        template = await self.prompts.get_template(template_id)
        if template is None:
            raise ResourceNotFoundError("Prompt template not found")
        after = payload.model_dump(mode="json", exclude={"idempotency_key"})
        if contains_sensitive_values(after):
            raise ParameterError("Prompt configuration cannot contain secrets")
        latest = await self.prompts.get_latest_version(template_id)
        before = (
            {"version": latest.version, "checksum": latest.checksum}
            if latest
            else {"version": None, "checksum": None}
        )
        return await self._request_change(
            operation_type=CREATE_PROMPT_VERSION,
            template_id=template_id,
            user_id=user_id,
            idempotency_key=payload.idempotency_key,
            before=before,
            after=after,
        )

    async def request_status_change(
        self,
        template_id: UUID,
        payload: PromptStatusChangeRequest,
        user_id: UUID,
    ) -> ConfirmationTask:
        template = await self.prompts.get_template(template_id)
        if template is None:
            raise ResourceNotFoundError("Prompt template not found")
        return await self._request_change(
            operation_type=SET_PROMPT_STATUS,
            template_id=template_id,
            user_id=user_id,
            idempotency_key=payload.idempotency_key,
            before={"status": template.status},
            after={"status": str(payload.status)},
        )

    async def _request_change(
        self,
        *,
        operation_type: str,
        template_id: UUID,
        user_id: UUID,
        idempotency_key: str,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> ConfirmationTask:
        confirmations = ConfirmationService(self.session)
        digest = hashlib.sha256(
            json.dumps(after, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        scope = confirmations.build_idempotency_scope(
            created_by=user_id,
            operation_type=operation_type,
            tool_name=None,
            tool_version=None,
            target_type="prompt_template",
            target_id=str(template_id),
            idempotency_key=idempotency_key,
        )
        existing = await confirmations.confirmations.get_by_idempotency_scope(scope)
        if existing is not None:
            if existing.input_digest != digest:
                raise IdempotencyConflictError()
            return existing
        task = await self.tasks.create_internal_task(
            task_type="prompt_management",
            user_input=f"Request {operation_type} for prompt template {template_id}",
            created_by=user_id,
        )
        await self.tasks.start(task.id)
        await self.tasks.wait_for_confirmation(task.id)
        return await confirmations.create(
            agent_task_id=task.id,
            operation_type=operation_type,
            target_type="prompt_template",
            target_id=str(template_id),
            risk_level=ToolRiskLevel.HIGH_RISK,
            idempotency_key=idempotency_key,
            created_by=user_id,
            before_snapshot=before,
            after_snapshot=after,
            input_digest=digest,
            risk_warning="确认后将修改 Prompt 配置。历史版本保持不可变，操作会记录审计日志。",
        )

    def register_executors(self, confirmations: ConfirmationService) -> None:
        confirmations.register_executor(CREATE_PROMPT_VERSION, self._execute_change)
        confirmations.register_executor(SET_PROMPT_STATUS, self._execute_change)

    async def _execute_change(self, confirmation: ConfirmationTask) -> dict[str, Any]:
        await self.tasks.start(confirmation.agent_task_id)
        template_id = UUID(str(confirmation.target_id))
        template = await self.prompts.get_template(template_id)
        if template is None:
            raise ResourceNotFoundError("Prompt template not found")
        data = confirmation.after_snapshot or {}
        if confirmation.operation_type == CREATE_PROMPT_VERSION:
            latest = await self.prompts.get_latest_version(template_id)
            checksum = hashlib.sha256(
                json.dumps(
                    {
                        "content": data["content"],
                        "input_schema": data["input_schema"],
                        "output_schema": data["output_schema"],
                        "model_parameters": data["model_parameters"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            if latest and latest.checksum == checksum:
                raise ParameterError("Prompt version content is unchanged")
            version = await self.prompts.add_version(
                PromptVersion(
                    template_id=template_id,
                    version=(latest.version + 1 if latest else 1),
                    content=data["content"],
                    input_schema=data["input_schema"],
                    output_schema=data["output_schema"],
                    model_config=data["model_parameters"],
                    change_summary=data["change_summary"],
                    checksum=checksum,
                    created_by=confirmation.confirmed_by or confirmation.created_by,
                )
            )
            result = {
                "template_id": str(template_id),
                "version_id": str(version.id),
                "version": version.version,
            }
        else:
            template.status = str(data["status"])
            result = {"template_id": str(template_id), "status": template.status}
        await self.tasks.complete(confirmation.agent_task_id, result)
        await self.logs.add(
            OperationLog(
                actor_id=confirmation.confirmed_by,
                action=confirmation.operation_type,
                target_type="prompt_template",
                target_id=str(template_id),
                request_id=confirmation.idempotency_key[:64],
                agent_task_id=confirmation.agent_task_id,
                confirmation_task_id=confirmation.id,
                risk_level=ToolRiskLevel.HIGH_RISK,
                before_snapshot=confirmation.before_snapshot,
                after_snapshot=result,
                status=OperationStatus.SUCCEEDED,
            )
        )
        return result

    async def model_runtime(self) -> ModelRuntimeSummary:
        rows, total = await self.invocations.list(1, 500)
        successes = sum(row.status == "succeeded" for row in rows)
        failures = sum(row.status == "failed" for row in rows)
        total_tokens = sum(row.total_tokens for row in rows)
        total_cost = sum((row.estimated_cost for row in rows), Decimal("0"))
        average_duration = sum(row.duration_ms for row in rows) / len(rows) if rows else 0
        key_configured = bool(
            self.settings.bailian_api_key and self.settings.bailian_api_key.get_secret_value()
        )
        return ModelRuntimeSummary(
            provider=self.settings.content_model_provider,
            model_name=self.settings.bailian_model,
            configured=(
                self.settings.content_model_provider == "offline_template"
                or (key_configured and bool(self.settings.bailian_base_url))
            ),
            base_url_configured=bool(self.settings.bailian_base_url),
            api_key_configured=key_configured,
            timeout_seconds=self.settings.bailian_timeout_seconds,
            invocation_count=total,
            success_count=successes,
            failure_count=failures,
            total_tokens=total_tokens,
            estimated_cost=total_cost,
            average_duration_ms=round(average_duration, 2),
        )

    async def list_invocations(self) -> list[ModelInvocationSummary]:
        rows, _ = await self.invocations.list(1, 100)
        return [ModelInvocationSummary.model_validate(row, from_attributes=True) for row in rows]

    async def evaluation(self) -> MemberThreeEvaluationSummary:
        dataset = (
            BACKEND_ROOT.parent / "data" / "evaluation" / "member3" / "v1" / "evaluation_cases.json"
        )
        report = await evaluate_member3(dataset)
        metrics = report.get("metrics") or {}
        failures = list(report.get("failures") or [])
        failed_categories = {
            str(item.get("category") or item.get("capability") or "unknown")
            for item in failures
            if isinstance(item, dict)
        }
        cases = [
            EvaluationCaseSummary(
                case_id=f"{category}-regression",
                category=category,
                passed=category not in failed_categories,
                metrics=dict(values) if isinstance(values, dict) else {"value": values},
                failures=[
                    str(item)
                    for item in failures
                    if isinstance(item, dict)
                    and str(item.get("category") or item.get("capability")) == category
                ],
            )
            for category, values in metrics.items()
        ]
        total = len(cases)
        passed = sum(item.passed for item in cases)
        generated = report.get("generated_at")
        return MemberThreeEvaluationSummary(
            dataset_version=str(report.get("dataset_version") or "member3-v1"),
            generated_at=datetime.fromisoformat(generated) if generated else None,
            total_cases=total,
            passed_cases=passed,
            failed_cases=max(total - passed, 0),
            pass_rate=round(passed / total, 4) if total else 0,
            cases=cases,
            limitations=[
                "离线模板评估不代表真实百炼模型质量。",
                "真实模型的成本、延迟和限流应在配置密钥后重新运行评估。",
            ],
        )

    @staticmethod
    def _prompt_version(row) -> PromptVersionSummary:
        return PromptVersionSummary(
            id=row.id,
            version=row.version,
            content=row.content,
            input_schema=row.input_schema,
            output_schema=row.output_schema,
            model_parameters=row.model_config,
            change_summary=row.change_summary,
            checksum=row.checksum,
            created_at=row.created_at,
        )
