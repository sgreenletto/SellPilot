from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import BACKEND_ROOT, Settings
from sellpilot.evaluation.member3 import evaluate_member3
from sellpilot.repositories.model_management import ModelInvocationRepository, PromptRepository
from sellpilot.schemas.ai_management import (
    EvaluationCaseSummary,
    MemberThreeEvaluationSummary,
    ModelInvocationSummary,
    ModelRuntimeSummary,
    PromptTemplateSummary,
    PromptVersionSummary,
)


class AIManagementService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.prompts = PromptRepository(session)
        self.invocations = ModelInvocationRepository(session)
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
        rows, _ = await self.prompts.list_versions(template_id, 1, 100)
        return [self._prompt_version(row) for row in rows]

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
