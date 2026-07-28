import hashlib
import json
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.core.enums import (
    ImprovementReportStatus,
    ImprovementSuggestionStatus,
    OperationStatus,
    ProductContentStatus,
    TaskType,
    ToolRiskLevel,
)
from sellpilot.core.exceptions import (
    IdempotencyConflictError,
    ParameterError,
    ResourceNotFoundError,
)
from sellpilot.db.models.analysis import (
    ProductImprovementReport,
    ProductImprovementSuggestion,
)
from sellpilot.db.models.confirmation_task import ConfirmationTask
from sellpilot.db.models.content import ProductContent, ProductContentVersion
from sellpilot.db.models.operation_log import OperationLog
from sellpilot.repositories.analysis import ImprovementRepository, ReviewAnalysisRepository
from sellpilot.repositories.content import ProductContentRepository
from sellpilot.repositories.operation_log import OperationLogRepository
from sellpilot.schemas.product_improvement import (
    ImprovementDraftRequest,
    ImprovementReportResponse,
    ImprovementSuggestionResponse,
    SuggestionUpdateRequest,
)
from sellpilot.services.confirmation import ConfirmationService
from sellpilot.services.product_improvement_gateway import ProductImprovementGateway
from sellpilot.services.task import TaskService

CREATE_DRAFT = "product_improvement.create_content_draft"
RULE_ALGORITHM_VERSION = "product-improvement-rule-v1.2.0"
LLM_ALGORITHM_VERSION = "product-improvement-aliyun-bailian-v1.0.0"

ACTION_BY_CATEGORY = {
    "product_quality": (
        "复核材料与结构失效点，定义关键质检项目和抽检标准；"
        "先用小批量样品完成耐用性验证，再决定是否调整量产工艺。"
    ),
    "packaging": (
        "按证据中的破损场景复核内衬、缓冲和封装方式；"
        "补充跌落与挤压测试，并记录改版前后的破损率用于验收。"
    ),
    "description_mismatch": (
        "逐项核对实物规格、尺寸、颜色和使用边界；"
        "修正商品页不一致信息，并用样品照片与规格表完成发布前复核。"
    ),
    "logistics": (
        "区分商品包装问题与承运时效问题，复核包装体积、承运方案和时效承诺；"
        "先在目标站点小范围验证后再扩大调整。"
    ),
    "service": "根据高频疑问补充使用说明、FAQ 和售后处理边界，并将新指引交由客服人工审核后使用。",
}

TITLE_BY_CATEGORY = {
    "product_quality": "降低产品质量相关差评",
    "packaging": "提升运输包装防护",
    "description_mismatch": "消除商品描述与实物偏差",
    "logistics": "改善物流与履约体验",
    "service": "完善使用说明与售后指引",
}


class ProductImprovementService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings
        self.reports = ImprovementRepository(session)
        self.analyses = ReviewAnalysisRepository(session)
        self.contents = ProductContentRepository(session)
        self.logs = OperationLogRepository(session)
        self.tasks = TaskService(session)

    async def generate(self, analysis_id: UUID, user_id: UUID) -> ImprovementReportResponse:
        analysis = await self.analyses.get_result(analysis_id)
        if analysis is None or analysis.created_by != user_id:
            raise ResourceNotFoundError("Review analysis not found")
        if str(analysis.status) != "SUCCEEDED":
            raise ParameterError("Review analysis must be completed before improvement planning")
        use_llm = (
            self.settings is not None and self.settings.content_model_provider == "aliyun_bailian"
        )
        algorithm_version = LLM_ALGORITHM_VERSION if use_llm else RULE_ALGORITHM_VERSION
        existing, _ = await self.reports.list_reports(
            1, 100, source_product_id=analysis.source_product_id
        )
        same_analysis = [item for item in existing if item.review_analysis_result_id == analysis_id]
        current = next(
            (item for item in same_analysis if item.algorithm_version == algorithm_version),
            None,
        )
        if current is not None:
            return await self.get_report(current.id, user_id)

        evidence, total = await self.analyses.list_evidence(analysis_id, 1, 5000)
        by_topic: dict[str, list] = {}
        for item in evidence:
            topic = self._effective_topic(item)
            if topic is not None:
                by_topic.setdefault(topic, []).append(item)
        summary = analysis.summary or {}
        sample_size = int(summary.get("quality", {}).get("included_count") or 0)
        negative_by_topic = {
            topic: [item for item in items if item.sentiment == "negative"]
            for topic, items in by_topic.items()
        }
        negative_by_topic = {topic: items for topic, items in negative_by_topic.items() if items}
        generated = {}
        if use_llm and negative_by_topic:
            gateway = ProductImprovementGateway(self.settings)
            generated = await gateway.generate(
                analysis.source_product_id,
                [
                    {
                        "category": topic,
                        "reviews": [
                            {
                                "review_id": item.source_review_id,
                                "original": item.excerpt,
                                "translation": item.translated_excerpt,
                            }
                            for item in items
                        ],
                    }
                    for topic, items in negative_by_topic.items()
                ],
            )
        suggestions: list[ProductImprovementSuggestion] = []
        for topic, negative in negative_by_topic.items():
            frequency = Decimal(len(negative)) / Decimal(max(sample_size, 1))
            avg_confidence = sum((item.confidence for item in negative), Decimal("0")) / Decimal(
                len(negative)
            )
            severity = min(Decimal("1"), frequency * Decimal("1.8") + Decimal("0.2"))
            priority = 1 if severity >= Decimal("0.75") else 2 if severity >= Decimal("0.5") else 3
            suggestions.append(
                ProductImprovementSuggestion(
                    suggestion_key=topic,
                    category=topic,
                    title=(
                        generated[topic].title
                        if topic in generated
                        else TITLE_BY_CATEGORY.get(topic, "复核高频评论问题")
                    ),
                    description=(
                        generated[topic].description
                        if topic in generated
                        else ACTION_BY_CATEGORY.get(
                            topic,
                            "基于代表评论复核该问题，并在改变商品前完成事实与样品验证。",
                        )
                    ),
                    priority=priority,
                    severity=severity.quantize(Decimal("0.0001")),
                    confidence=min(
                        Decimal("1"),
                        avg_confidence * min(Decimal("1"), Decimal(len(negative)) / Decimal("5")),
                    ).quantize(Decimal("0.0001")),
                    evidence_count=len(negative),
                    frequency_rate=frequency.quantize(Decimal("0.0001")),
                    evidence_review_ids={"items": [item.source_review_id for item in negative]},
                    expected_impact={
                        "direction": "reduce_negative_feedback",
                        "limitations": "规则建议；实施前需核对商品事实、成本与工厂可行性。",
                    },
                    status=ImprovementSuggestionStatus.PROPOSED,
                )
            )
        suggestions.sort(key=lambda item: (item.priority, -item.severity, item.suggestion_key))
        report = ProductImprovementReport(
            review_analysis_result_id=analysis_id,
            source_product_id=analysis.source_product_id,
            version=max((item.version for item in same_analysis), default=0) + 1,
            algorithm_version=algorithm_version,
            status=ImprovementReportStatus.READY,
            source_type=analysis.source_type,
            is_mock_data=analysis.is_mock_data,
            data_sources={
                "analysis_id": str(analysis_id),
                "evidence_count": total,
                "evidence_review_ids": sorted({item.source_review_id for item in evidence}),
            },
            input_conditions=analysis.input_conditions,
            summary={
                "sample_size": sample_size,
                "suggestion_count": len(suggestions),
                "limitations": [
                    "Mock Shopee 模拟数据",
                    (
                        f"由 {self.settings.bailian_model} 基于限定证据生成"
                        if use_llm
                        else "未配置模型时使用确定性规则生成"
                    ),
                    "工厂实施前必须核对商品事实与成本",
                ],
            },
            created_by=user_id,
        )
        await self.reports.add_report(report)
        for suggestion in suggestions:
            suggestion.report_id = report.id
        await self.reports.add_suggestions(suggestions)
        await self.session.commit()
        return await self.get_report(report.id, user_id)

    @staticmethod
    def _effective_topic(item) -> str | None:
        text = f"{item.excerpt or ''} {item.translated_excerpt or ''}".casefold()
        if item.label != "description_mismatch":
            return item.label
        aligned = any(
            phrase in text
            for phrase in (
                "matches the photo",
                "works as described",
                "与图片一致",
                "符合描述",
            )
        )
        if not aligned:
            return item.label
        if any(phrase in text for phrase in ("finish", "basic", "工艺", "做工")):
            return "product_quality"
        return None

    async def get_report(self, report_id: UUID, user_id: UUID) -> ImprovementReportResponse:
        report = await self.reports.get_report(report_id)
        if report is None or report.created_by != user_id:
            raise ResourceNotFoundError("Improvement report not found")
        suggestions, _ = await self.reports.list_suggestions(report_id, 1, 100)
        return self._response(report, suggestions)

    async def update_suggestion(
        self, suggestion_id: UUID, payload: SuggestionUpdateRequest, user_id: UUID
    ) -> ImprovementSuggestionResponse:
        suggestion = await self.reports.get_suggestion(suggestion_id)
        if suggestion is None:
            raise ResourceNotFoundError("Improvement suggestion not found")
        report = await self.reports.get_report(suggestion.report_id)
        if report is None or report.created_by != user_id:
            raise ResourceNotFoundError("Improvement suggestion not found")
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(suggestion, field, value)
        await self.session.commit()
        return ImprovementSuggestionResponse.model_validate(suggestion)

    async def export(self, report_id: UUID, user_id: UUID) -> dict[str, Any]:
        report = await self.get_report(report_id, user_id)
        lines = [
            f"# {report.source_product_id} 产品改良报告",
            "",
            f"- 报告版本：v{report.version}",
            f"- 分析方式：{report.algorithm_version}",
            f"- 有效评论：{report.summary.get('sample_size', 0)}",
            f"- 改良建议：{len(report.suggestions)}",
            "- 数据边界：Mock Shopee 模拟数据，实施前需人工核对",
            "",
            "## 改良建议",
            "",
        ]
        if not report.suggestions:
            lines.append("当前分析没有低评分或含明确缺点的评论证据，因此未生成改良建议。")
        for index, suggestion in enumerate(report.suggestions, start=1):
            lines.extend(
                [
                    f"### {index}. {suggestion.title}",
                    "",
                    f"- 优先级：P{suggestion.priority}",
                    f"- 依据：{suggestion.evidence_count} 条相关评论",
                    "",
                    suggestion.description,
                    "",
                ]
            )
        return {
            "format": "markdown",
            "filename": f"product-improvement-{report.source_product_id}-v{report.version}.md",
            "content": "\n".join(lines),
        }

    async def request_draft(
        self, report_id: UUID, payload: ImprovementDraftRequest, user_id: UUID
    ) -> ConfirmationTask:
        report = await self.get_report(report_id, user_id)
        selected = [item for item in report.suggestions if item.id in payload.suggestion_ids]
        if len(selected) != len(set(payload.suggestion_ids)):
            raise ParameterError("All selected suggestions must belong to the report")
        after = {
            "report_id": str(report_id),
            "source_product_id": report.source_product_id,
            "site": payload.site,
            "target_language": payload.target_language,
            "suggestions": [item.model_dump(mode="json") for item in selected],
        }
        digest = hashlib.sha256(
            json.dumps(after, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        confirmations = ConfirmationService(self.session)
        scope = confirmations.build_idempotency_scope(
            created_by=user_id,
            operation_type=CREATE_DRAFT,
            tool_name=None,
            tool_version=None,
            target_type="product_content",
            target_id=report.source_product_id,
            idempotency_key=payload.idempotency_key,
        )
        existing = await confirmations.confirmations.get_by_idempotency_scope(scope)
        if existing is not None:
            if existing.input_digest != digest:
                raise IdempotencyConflictError()
            return existing
        task = await self.tasks.create_internal_task(
            task_type=TaskType.PRODUCT_IMPROVEMENT,
            user_input=f"Create improvement content draft for {report.source_product_id}",
            created_by=user_id,
        )
        await self.tasks.start(task.id)
        await self.tasks.wait_for_confirmation(task.id)
        return await confirmations.create(
            agent_task_id=task.id,
            operation_type=CREATE_DRAFT,
            target_type="product_content",
            target_id=report.source_product_id,
            risk_level=ToolRiskLevel.HIGH_RISK,
            idempotency_key=payload.idempotency_key,
            created_by=user_id,
            before_snapshot={"status": "not_created"},
            after_snapshot=after,
            input_digest=digest,
            risk_warning="确认后仅创建 Mock 商品内容草稿，不发布、不改价、不改库存。",
        )

    def register_executors(self, confirmations: ConfirmationService) -> None:
        confirmations.register_executor(CREATE_DRAFT, self._execute_draft)

    async def _execute_draft(self, confirmation: ConfirmationTask) -> dict[str, Any]:
        payload = confirmation.after_snapshot or {}
        await self.tasks.start(confirmation.agent_task_id)
        try:
            content = await self.session.scalar(
                select(ProductContent).where(
                    ProductContent.source_product_id == payload["source_product_id"],
                    ProductContent.site == payload["site"],
                    ProductContent.target_language == payload["target_language"],
                )
            )
            if content is None:
                content = ProductContent(
                    source_product_id=payload["source_product_id"],
                    site=payload["site"],
                    target_language=payload["target_language"],
                    status=ProductContentStatus.DRAFT,
                    source_type="mock_shopee",
                    source_facts={"improvement_report_id": payload["report_id"]},
                    is_mock_data=True,
                    agent_task_id=confirmation.agent_task_id,
                    created_by=confirmation.created_by,
                )
                await self.contents.add_content(content)
            versions, _ = await self.contents.list_versions(content.id, 1, 1)
            next_version = versions[0].version + 1 if versions else 1
            version = ProductContentVersion(
                content_id=content.id,
                version=next_version,
                title=f"{payload['source_product_id']} 改良内容草稿",
                bullet_points={"items": [item["title"] for item in payload["suggestions"]]},
                description="\n".join(item["description"] for item in payload["suggestions"]),
                marketing_copy="待人工完善的改良内容草稿",
                source_facts_snapshot=content.source_facts,
                fact_check_result={"status": "requires_human_review"},
                compliance_result={"status": "not_checked"},
                change_type="improvement_draft",
                change_summary="基于已采纳评论改良建议创建",
                created_by=confirmation.created_by,
            )
            await self.contents.add_version(version)
            result = {
                "content_id": str(content.id),
                "version_id": str(version.id),
                "status": "DRAFT",
            }
            await self.tasks.complete(confirmation.agent_task_id, result)
            await self.logs.add(
                OperationLog(
                    actor_id=confirmation.confirmed_by,
                    action=CREATE_DRAFT,
                    target_type="product_content",
                    target_id=str(content.id),
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
                "IMPROVEMENT_DRAFT_FAILED",
                type(exc).__name__,
            )
            raise

    @staticmethod
    def _response(report, suggestions) -> ImprovementReportResponse:
        summary = dict(report.summary or {})
        unique_review_ids = (report.data_sources or {}).get("evidence_review_ids", [])
        if isinstance(unique_review_ids, list):
            summary["sample_size"] = len(set(unique_review_ids))
        return ImprovementReportResponse(
            id=report.id,
            review_analysis_result_id=report.review_analysis_result_id,
            source_product_id=report.source_product_id,
            version=report.version,
            algorithm_version=report.algorithm_version,
            status=report.status,
            source_type=report.source_type,
            is_mock_data=report.is_mock_data,
            data_sources=report.data_sources,
            input_conditions=report.input_conditions,
            summary=summary,
            created_at=report.created_at,
            suggestions=[
                ImprovementSuggestionResponse.model_validate(item) for item in suggestions
            ],
        )
