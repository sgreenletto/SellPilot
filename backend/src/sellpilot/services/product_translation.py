import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

import httpx
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.core.enums import TaskType, ToolRiskLevel
from sellpilot.core.exceptions import (
    IdempotencyConflictError,
    ResourceNotFoundError,
)
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.schemas.product_translation import (
    ProductTranslationFailure,
    ProductTranslationProviderStatus,
    ProductTranslationRequest,
    ProductTranslationResult,
    ProductTranslationTask,
)
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.services.task import TaskService

TRANSLATE_PRODUCT = "product_translation.translate"
SUPPORTED_LANGUAGES = ["en", "zh-CN", "zh-TW", "ms", "id", "th", "vi", "tl", "pt-BR"]


class ProductTranslationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.tasks = TaskService(session)

    def provider_status(self) -> ProductTranslationProviderStatus:
        configured = (
            self.settings.content_model_provider == "aliyun_bailian"
            and bool(self.settings.bailian_base_url)
            and bool(
                self.settings.bailian_api_key and self.settings.bailian_api_key.get_secret_value()
            )
        )
        return ProductTranslationProviderStatus(
            configured=configured,
            provider="aliyun_bailian" if configured else None,
            supported_languages=SUPPORTED_LANGUAGES,
        )

    async def request(
        self, payload: ProductTranslationRequest, user_id: UUID
    ) -> ProductTranslationTask:
        snapshot = payload.model_dump(mode="json")
        digest = hashlib.sha256(
            json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        confirmations = ConfirmationService(self.session)
        scope = confirmations.build_idempotency_scope(
            created_by=user_id,
            operation_type=TRANSLATE_PRODUCT,
            tool_name=None,
            tool_version=None,
            target_type="product_translation",
            target_id=payload.source.product_id,
            idempotency_key=payload.idempotency_key,
        )
        existing = await confirmations.confirmations.get_by_idempotency_scope(scope)
        if existing:
            if existing.input_digest != digest:
                raise IdempotencyConflictError()
            return self._response(existing)
        task = await self.tasks.create_internal_task(
            task_type=TaskType.CONTENT_GENERATION,
            user_input=f"Translate Mock product {payload.source.product_id}",
            created_by=user_id,
        )
        await self.tasks.start(task.id)
        await self.tasks.wait_for_confirmation(task.id)
        confirmation = await confirmations.create(
            agent_task_id=task.id,
            operation_type=TRANSLATE_PRODUCT,
            target_type="product_translation",
            target_id=payload.source.product_id,
            risk_level=ToolRiskLevel.HIGH_RISK,
            idempotency_key=payload.idempotency_key,
            created_by=user_id,
            before_snapshot={
                "source_language": payload.source.source_language,
                "is_mock_data": True,
            },
            after_snapshot=snapshot,
            input_digest=digest,
            risk_warning=(
                "确认后会把当前 Mock 商品字段发送给已配置的阿里云百炼进行翻译；"
                "结果只返回前端，不修改商品、价格或库存。"
            ),
        )
        await self.session.commit()
        return self._response(confirmation)

    async def get(self, task_id: UUID, user_id: UUID) -> ProductTranslationTask:
        confirmation = await self.session.scalar(
            select(ConfirmationTask).where(
                ConfirmationTask.agent_task_id == task_id,
                ConfirmationTask.created_by == user_id,
                ConfirmationTask.operation_type == TRANSLATE_PRODUCT,
            )
        )
        if confirmation is None:
            raise ResourceNotFoundError("Product translation task not found")
        return self._response(confirmation)

    def register_executor(self, confirmations: ConfirmationService) -> None:
        confirmations.register_executor(TRANSLATE_PRODUCT, self._execute)

    async def _execute(self, confirmation: ConfirmationTask) -> dict[str, object]:
        payload = ProductTranslationRequest.model_validate(confirmation.after_snapshot)
        await self.tasks.start(confirmation.agent_task_id)
        results: list[dict[str, object]] = []
        failures: list[dict[str, object]] = []
        for language in payload.target_languages:
            try:
                translated = await self._translate(payload, language)
                results.append(translated.model_dump(mode="json"))
            except Exception as exc:
                failures.append(
                    ProductTranslationFailure(
                        language=language,
                        code=type(exc).__name__,
                        message="Translation provider failed or returned invalid structured data",
                    ).model_dump(mode="json")
                )
        status = (
            "succeeded" if results and not failures else "partially_failed" if results else "failed"
        )
        output = {"status": status, "results": results, "failed_languages": failures}
        if results:
            await self.tasks.complete(confirmation.agent_task_id, output)
        else:
            await self.tasks.fail(
                confirmation.agent_task_id,
                "PRODUCT_TRANSLATION_FAILED",
                "All target languages failed",
            )
        return output

    async def _translate(
        self, payload: ProductTranslationRequest, language: str
    ) -> ProductTranslationResult:
        status = self.provider_status()
        if not status.configured:
            raise RuntimeError("Aliyun Bailian product translation is not configured")
        source = payload.source.model_dump(mode="json")
        request_payload = {
            "model": self.settings.bailian_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Translate ecommerce product fields faithfully. Return one JSON object "
                        "with language, title, description, category_name and specifications. "
                        "Preserve numbers, units, identifiers and technical facts exactly. "
                        "Do not add claims or facts."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "source": source,
                            "target_language": language,
                            "fields": payload.fields,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        api_key = self.settings.bailian_api_key.get_secret_value()
        async with httpx.AsyncClient(timeout=self.settings.bailian_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.bailian_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=request_payload,
            )
            response.raise_for_status()
        raw = json.loads(response.json()["choices"][0]["message"]["content"])
        raw.update(
            language=language,
            provider="aliyun_bailian",
            generated_at=datetime.now(UTC),
        )
        try:
            return TypeAdapter(ProductTranslationResult).validate_python(raw)
        except ValidationError:
            raise RuntimeError("Invalid product translation schema") from None

    @staticmethod
    def _response(confirmation: ConfirmationTask) -> ProductTranslationTask:
        execution = confirmation.execution_result or {}
        status = (
            "pending_confirmation"
            if str(confirmation.status) == "pending"
            else str(execution.get("status") or "running")
        )
        return ProductTranslationTask(
            task_id=confirmation.agent_task_id,
            confirmation_task_id=confirmation.id,
            status=status,
            results=execution.get("results") or [],
            failed_languages=execution.get("failed_languages") or [],
        )
