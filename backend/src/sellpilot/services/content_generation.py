import hashlib
import json
import time
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.adapters.factory import create_platform_adapter
from sellpilot.core.config import Settings
from sellpilot.core.enums import (
    ModelInvocationStatus,
    OperationStatus,
    ProductContentStatus,
    PromptStatus,
    TaskType,
    ToolRiskLevel,
)
from sellpilot.core.exceptions import (
    IdempotencyConflictError,
    ParameterError,
    ResourceNotFoundError,
)
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.db.models.content import ProductContent, ProductContentVersion
from sellpilot.db.models.model_management import (
    ModelInvocation,
    PromptTemplate,
    PromptVersion,
)
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.domain.content_generation.models import (
    ListingFacts,
    LocalizedListing,
    ModelGateway,
)
from sellpilot.domain.content_generation.workflow import check_listing, generate_with_quality_loop
from sellpilot.repositories.content import ProductContentRepository
from sellpilot.repositories.model_management import (
    ModelInvocationRepository,
    PromptRepository,
)
from sellpilot.repositories.operation_log import OperationLogRepository
from sellpilot.schemas.content_generation import (
    ContentDraftRequest,
    ContentExportResponse,
    ContentGenerateRequest,
    ContentGenerateResponse,
    ContentRegenerateFieldRequest,
    ContentRegenerateFieldResponse,
    ContentRestoreRequest,
    ContentVersionComparisonResponse,
    ContentVersionResponse,
    ContentVersionsResponse,
)
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.services.model_gateway import build_model_gateway
from sellpilot.services.task import TaskService

SAVE_DRAFT = "content_generation.save_draft"
RESTORE_VERSION = "content_generation.restore_version"
PROMPT_KEY = "localized-listing-v1"


class ContentGenerationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.adapter = create_platform_adapter(settings, session)
        self.contents = ProductContentRepository(session)
        self.prompts = PromptRepository(session)
        self.invocations = ModelInvocationRepository(session)
        self.tasks = TaskService(session)
        self.logs = OperationLogRepository(session)

    async def generate(
        self, payload: ContentGenerateRequest, user_id: UUID
    ) -> ContentGenerateResponse:
        facts = await self._listing_facts(payload)
        gateway = build_model_gateway(self.settings)
        task = await self.tasks.create_internal_task(
            task_type=TaskType.CONTENT_GENERATION,
            user_input=f"Generate {payload.target_language} content for {payload.product_id}",
            created_by=user_id,
        )
        await self.tasks.start(task.id)
        prompt = await self._prompt(user_id, gateway)
        started = time.perf_counter()
        input_payload = facts.model_dump(mode="json")
        digest = hashlib.sha256(
            json.dumps(input_payload, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        invocation = ModelInvocation(
            agent_task_id=task.id,
            prompt_version_id=prompt.id,
            provider=gateway.provider,
            model_name=gateway.model_name,
            status=ModelInvocationStatus.RUNNING,
            input_digest=digest,
            input_summary={
                "product_id": payload.product_id,
                "site": payload.site,
                "target_language": payload.target_language,
                "field_count": len(input_payload),
            },
            output_summary=None,
            model_parameters={"max_attempts": payload.max_attempts, "temperature": 0},
            timeout_ms=30_000,
            retry_count=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            duration_ms=0,
            estimated_cost=Decimal("0"),
            cost_currency="USD",
            created_by=user_id,
        )
        await self.invocations.add(invocation)
        try:
            generated = await generate_with_quality_loop(gateway, facts, payload.max_attempts)
            invocation.prompt_tokens = gateway.prompt_tokens
            invocation.completion_tokens = gateway.completion_tokens
            invocation.total_tokens = gateway.total_tokens
            invocation.estimated_cost = (
                Decimal(gateway.prompt_tokens) * self.settings.bailian_input_cost_per_million
                + Decimal(gateway.completion_tokens) * self.settings.bailian_output_cost_per_million
            ) / Decimal("1000000")
            invocation.status = ModelInvocationStatus.SUCCEEDED
            invocation.duration_ms = int((time.perf_counter() - started) * 1000)
            invocation.output_summary = {
                "passed": generated.quality.passed,
                "attempts": generated.quality.attempts,
                "generation_mode": generated.content.generation_mode,
            }
            if not generated.quality.passed:
                await self.tasks.fail(task.id, "CONTENT_QUALITY_FAILED", "Quality loop exhausted")
            else:
                await self.tasks.complete(task.id, invocation.output_summary)
            await self.session.commit()
            return ContentGenerateResponse(
                task_id=task.id,
                product_id=payload.product_id,
                site=payload.site,
                target_language=payload.target_language,
                audience=payload.audience,
                selling_points=payload.selling_points,
                keywords=payload.keywords,
                result=generated,
                provider=gateway.provider,
                model_name=gateway.model_name,
                invocation_id=invocation.id,
            )
        except Exception as exc:
            invocation.prompt_tokens = gateway.prompt_tokens
            invocation.completion_tokens = gateway.completion_tokens
            invocation.total_tokens = gateway.total_tokens
            invocation.status = ModelInvocationStatus.FAILED
            invocation.duration_ms = int((time.perf_counter() - started) * 1000)
            invocation.error_code = type(exc).__name__
            invocation.error_message = "Structured generation failed"
            await self.tasks.fail(task.id, "CONTENT_GENERATION_FAILED", type(exc).__name__)
            await self.session.commit()
            raise

    async def request_draft(self, payload: ContentDraftRequest, user_id: UUID) -> ConfirmationTask:
        generation = payload.generation
        invocation = await self.invocations.get(generation.invocation_id)
        source_task = await self.session.get(AgentTask, generation.task_id)
        if (
            invocation is None
            or source_task is None
            or invocation.agent_task_id != generation.task_id
            or source_task.created_by != user_id
            or invocation.provider != generation.provider
            or invocation.model_name != generation.model_name
        ):
            raise ResourceNotFoundError("Content generation result not found")
        request = ContentGenerateRequest(
            product_id=generation.product_id,
            site=generation.site,
            target_language=generation.target_language,
            audience=generation.audience,
            selling_points=generation.selling_points,
            keywords=generation.keywords,
        )
        facts = await self._listing_facts(request)
        facts_digest = hashlib.sha256(
            json.dumps(
                facts.model_dump(mode="json"),
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        if invocation.input_digest != facts_digest:
            raise ParameterError("Generation request facts no longer match the source invocation")
        quality = check_listing(generation.result.content, facts, attempts=1)
        if not quality.passed:
            raise ParameterError("Content that failed quality checks cannot be saved")
        after = generation.model_dump(mode="json")
        after["result"]["quality"] = quality.model_dump(mode="json")
        return await self._confirmation(
            operation=SAVE_DRAFT,
            target_id=generation.product_id,
            after=after,
            idempotency_key=payload.idempotency_key,
            user_id=user_id,
        )

    async def _listing_facts(self, payload: ContentGenerateRequest) -> ListingFacts:
        raw = await self.adapter.get_product(payload.product_id)
        if not raw:
            raise ResourceNotFoundError("Product not found")
        facts = ListingFacts(
            product_id=payload.product_id,
            title=str(raw.get("title") or ""),
            description=str(raw.get("description") or ""),
            category_name=str(raw.get("category_name") or "Product"),
            site=payload.site,
            target_language=payload.target_language,
            audience=payload.audience,
            selling_points=payload.selling_points,
            requested_keywords=payload.keywords,
            specifications={
                str(item.get("name")): str(item.get("value"))
                for item in raw.get("specifications", [])
                if isinstance(item, dict) and item.get("name") and item.get("value")
            },
            sku_facts=list(raw.get("skus") or []),
        )
        if not facts.title or not facts.description:
            raise ParameterError("Product title and description facts are required")
        return facts

    async def request_restore(
        self,
        content_id: UUID,
        payload: ContentRestoreRequest,
        user_id: UUID,
    ) -> ConfirmationTask:
        content = await self.contents.get_content(content_id)
        version = await self.contents.get_version(payload.version_id)
        if (
            content is None
            or version is None
            or version.content_id != content_id
            or content.created_by != user_id
        ):
            raise ResourceNotFoundError("Content version not found")
        after = {"content_id": str(content_id), "version_id": str(version.id)}
        return await self._confirmation(
            operation=RESTORE_VERSION,
            target_id=str(content_id),
            after=after,
            idempotency_key=payload.idempotency_key,
            user_id=user_id,
        )

    async def list_versions(self, content_id: UUID, user_id: UUID) -> ContentVersionsResponse:
        content = await self.contents.get_content(content_id)
        if content is None or content.created_by != user_id:
            raise ResourceNotFoundError("Product content not found")
        rows, total = await self.contents.list_versions(content_id, 1, 100)
        return ContentVersionsResponse(
            content_id=content_id,
            items=[self._version_response(item) for item in rows],
            total=total,
        )

    async def get_version(
        self, content_id: UUID, version_id: UUID, user_id: UUID
    ) -> ContentVersionResponse:
        content = await self.contents.get_content(content_id)
        version = await self.contents.get_version(version_id)
        if (
            content is None
            or version is None
            or version.content_id != content_id
            or content.created_by != user_id
        ):
            raise ResourceNotFoundError("Content version not found")
        return self._version_response(version)

    async def compare_versions(
        self,
        content_id: UUID,
        left_id: UUID,
        right_id: UUID,
        user_id: UUID,
    ) -> ContentVersionComparisonResponse:
        left = await self.get_version(content_id, left_id, user_id)
        right = await self.get_version(content_id, right_id, user_id)
        fields = (
            "title",
            "bullet_points",
            "description",
            "marketing_copy",
            "faq",
            "sku_content",
            "keywords",
            "fact_check_result",
            "compliance_result",
        )
        return ContentVersionComparisonResponse(
            content_id=content_id,
            left=left,
            right=right,
            changed_fields=[
                field for field in fields if getattr(left, field) != getattr(right, field)
            ],
        )

    async def regenerate_field(
        self,
        payload: ContentRegenerateFieldRequest,
        user_id: UUID,
    ) -> ContentRegenerateFieldResponse:
        generation = await self.generate(payload.request, user_id)
        return ContentRegenerateFieldResponse(
            task_id=generation.task_id,
            invocation_id=generation.invocation_id,
            field=payload.field,
            value=getattr(generation.result.content, payload.field),
            quality=generation.result.quality.model_dump(mode="json"),
            provider=generation.provider,
            model_name=generation.model_name,
        )

    async def export_version(
        self, content_id: UUID, version_id: UUID, user_id: UUID
    ) -> ContentExportResponse:
        version = await self.get_version(content_id, version_id, user_id)
        payload = version.model_dump(mode="json")
        return ContentExportResponse(
            filename=f"sellpilot-content-v{version.version}.json",
            media_type="application/json",
            content=json.dumps(payload, ensure_ascii=False, indent=2),
        )

    async def _confirmation(
        self,
        *,
        operation: str,
        target_id: str,
        after: dict[str, Any],
        idempotency_key: str,
        user_id: UUID,
    ) -> ConfirmationTask:
        digest = hashlib.sha256(
            json.dumps(after, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        confirmations = ConfirmationService(self.session)
        scope = confirmations.build_idempotency_scope(
            created_by=user_id,
            operation_type=operation,
            tool_name=None,
            tool_version=None,
            target_type="product_content",
            target_id=target_id,
            idempotency_key=idempotency_key,
        )
        existing = await confirmations.confirmations.get_by_idempotency_scope(scope)
        if existing is not None:
            if existing.input_digest != digest:
                raise IdempotencyConflictError()
            return existing
        task = await self.tasks.create_internal_task(
            task_type=TaskType.CONTENT_GENERATION,
            user_input=f"Request {operation} for {target_id}",
            created_by=user_id,
        )
        await self.tasks.start(task.id)
        await self.tasks.wait_for_confirmation(task.id)
        return await confirmations.create(
            agent_task_id=task.id,
            operation_type=operation,
            target_type="product_content",
            target_id=target_id,
            risk_level=ToolRiskLevel.HIGH_RISK,
            idempotency_key=idempotency_key,
            created_by=user_id,
            before_snapshot={"status": "unchanged"},
            after_snapshot=after,
            input_digest=digest,
            risk_warning="确认后创建新的 Mock 商品内容版本；不会发布、改价或修改库存。",
        )

    def register_executors(self, confirmations: ConfirmationService) -> None:
        confirmations.register_executor(SAVE_DRAFT, self._execute)
        confirmations.register_executor(RESTORE_VERSION, self._execute)

    async def _execute(self, confirmation: ConfirmationTask) -> dict[str, Any]:
        await self.tasks.start(confirmation.agent_task_id)
        try:
            if confirmation.operation_type == RESTORE_VERSION:
                result = await self._restore(confirmation)
            else:
                result = await self._save(confirmation)
            await self.tasks.complete(confirmation.agent_task_id, result)
            await self.logs.add(
                OperationLog(
                    actor_id=confirmation.confirmed_by,
                    action=confirmation.operation_type,
                    target_type="product_content",
                    target_id=result["content_id"],
                    request_id=confirmation.idempotency_key[:64],
                    agent_task_id=confirmation.agent_task_id,
                    confirmation_task_id=confirmation.id,
                    before_snapshot=confirmation.before_snapshot,
                    after_snapshot=result,
                    status=OperationStatus.SUCCEEDED,
                )
            )
            return result
        except Exception as exc:
            await self.tasks.fail(
                confirmation.agent_task_id,
                "CONTENT_VERSION_WRITE_FAILED",
                type(exc).__name__,
            )
            raise

    async def _save(self, confirmation: ConfirmationTask) -> dict[str, Any]:
        data = confirmation.after_snapshot or {}
        result = data["result"]
        localized = result["content"]
        quality = result["quality"]
        content = await self.session.scalar(
            select(ProductContent).where(
                ProductContent.source_product_id == data["product_id"],
                ProductContent.site == data["site"],
                ProductContent.target_language == data["target_language"],
            )
        )
        if content is None:
            content = ProductContent(
                source_product_id=data["product_id"],
                site=data["site"],
                target_language=data["target_language"],
                status=ProductContentStatus.PASSED,
                source_type="mock_shopee",
                source_snapshot_version=data["invocation_id"],
                source_facts={"product_id": data["product_id"]},
                is_mock_data=True,
                agent_task_id=confirmation.agent_task_id,
                created_by=confirmation.created_by,
            )
            await self.contents.add_content(content)
        rows, _ = await self.contents.list_versions(content.id, 1, 1)
        number = rows[0].version + 1 if rows else 1
        version = ProductContentVersion(
            content_id=content.id,
            version=number,
            title=localized["title"],
            bullet_points={"items": localized["bullet_points"]},
            description=localized["description"],
            marketing_copy=localized["marketing_copy"],
            faq={"items": localized["faq"]},
            sku_content={"items": localized["sku_content"]},
            keywords={"items": localized["keywords"]},
            source_facts_snapshot=content.source_facts,
            fact_check_result={
                "passed": not quality["fact_issues"],
                "issues": quality["fact_issues"],
            },
            compliance_result={
                "passed": not quality["compliance_issues"],
                "issues": quality["compliance_issues"],
            },
            change_type="generated",
            change_summary=f"{localized['generation_mode']} localized generation",
            model_invocation_id=UUID(data["invocation_id"]),
            created_by=confirmation.created_by,
        )
        await self.contents.add_version(version)
        return {
            "content_id": str(content.id),
            "version_id": str(version.id),
            "version": number,
            "status": "DRAFT",
        }

    async def _restore(self, confirmation: ConfirmationTask) -> dict[str, Any]:
        data = confirmation.after_snapshot or {}
        content = await self.contents.get_content(UUID(data["content_id"]))
        source = await self.contents.get_version(UUID(data["version_id"]))
        if content is None or source is None or source.content_id != content.id:
            raise ResourceNotFoundError("Content version not found")
        rows, _ = await self.contents.list_versions(content.id, 1, 1)
        number = rows[0].version + 1 if rows else 1
        clone = ProductContentVersion(
            content_id=content.id,
            version=number,
            title=source.title,
            bullet_points=source.bullet_points,
            description=source.description,
            marketing_copy=source.marketing_copy,
            faq=source.faq,
            sku_content=source.sku_content,
            keywords=source.keywords,
            source_facts_snapshot=source.source_facts_snapshot,
            fact_check_result=source.fact_check_result,
            compliance_result=source.compliance_result,
            change_type="restore",
            change_summary=f"Restore version {source.version}",
            prompt_version_id=source.prompt_version_id,
            model_invocation_id=source.model_invocation_id,
            created_by=confirmation.created_by,
        )
        await self.contents.add_version(clone)
        return {
            "content_id": str(content.id),
            "version_id": str(clone.id),
            "version": number,
            "status": "DRAFT",
        }

    async def _prompt(self, user_id: UUID, gateway: ModelGateway) -> PromptVersion:
        prompt_key = f"{PROMPT_KEY}-{gateway.provider}"
        template = await self.prompts.get_template_by_key(prompt_key)
        if template is None:
            template = PromptTemplate(
                key=prompt_key,
                name="Localized listing generation",
                purpose="Generate structured localized listing content from verified facts",
                task_type="content_generation",
                language="multi",
                status=PromptStatus.ACTIVE,
                created_by=user_id,
            )
            await self.prompts.add_template(template)
        latest = await self.prompts.get_latest_version(template.id)
        if latest is not None:
            return latest
        content = (
            "Use only verified product facts. Return the required structured schema. "
            "Never invent material, dimensions, quantity, SKU, price, certification, or claims."
        )
        checksum = hashlib.sha256(content.encode()).hexdigest()
        version = PromptVersion(
            template_id=template.id,
            version=1,
            content=content,
            input_schema=ListingFacts.model_json_schema(),
            output_schema=LocalizedListing.model_json_schema(),
            model_config={
                "provider": gateway.provider,
                "model": gateway.model_name,
                "temperature": 0.1 if gateway.provider == "aliyun_bailian" else 0,
                "response_format": "json_object",
            },
            change_summary="Initial safe structured content prompt",
            checksum=checksum,
            created_by=user_id,
        )
        await self.prompts.add_version(version)
        return version

    @staticmethod
    def _version_response(item: ProductContentVersion) -> ContentVersionResponse:
        return ContentVersionResponse.model_validate(jsonable_encoder(item), from_attributes=True)
