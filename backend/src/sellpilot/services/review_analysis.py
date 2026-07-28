import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.config import Settings
from sellpilot.core.enums import (
    AnalysisStatus,
    DataSource,
    SiteCode,
    TaskStatus,
    TaskType,
)
from sellpilot.core.exceptions import (
    IdempotencyConflictError,
    ResourceNotFoundError,
    StateConflictError,
)
from sellpilot.db.models.analysis import ReviewAnalysisEvidence, ReviewAnalysisResult
from sellpilot.domain.review_analysis import (
    ReviewAnalysisReport,
    ReviewInput,
    ReviewTopic,
    classify_review_preview,
)
from sellpilot.repositories.analysis import ReviewAnalysisRepository
from sellpilot.schemas.common import SourceMetadata
from sellpilot.schemas.review_analysis import (
    ReviewAnalysisCreatedResponse,
    ReviewAnalysisCreateRequest,
    ReviewAnalysisExportResponse,
    ReviewAnalysisResultResponse,
    ReviewEvidencePage,
    ReviewEvidenceResponse,
    ReviewQuery,
    ReviewResponse,
)
from sellpilot.services.commerce_query import CommerceQueryService
from sellpilot.services.model_gateway import translate_review_batch
from sellpilot.services.task import TaskService
from sellpilot.workflows.review_analysis import ReviewAnalyzer, build_review_analysis_workflow

SITE_NAMES = {
    SiteCode.SG: "Singapore",
    SiteCode.MY: "Malaysia",
    SiteCode.PH: "Philippines",
    SiteCode.TH: "Thailand",
    SiteCode.VN: "Vietnam",
    SiteCode.ID: "Indonesia",
}
SITE_CODES = {value: key for key, value in SITE_NAMES.items()}
STEP_NAMES = ("load_reviews", "analyze_reviews", "persist_results")


class ReviewAnalysisService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        *,
        analyzer: ReviewAnalyzer | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.commerce = CommerceQueryService(session, settings)
        self.analysis = ReviewAnalysisRepository(session)
        self.tasks = TaskService(session)
        self.workflow = (
            build_review_analysis_workflow(analyzer)
            if analyzer
            else build_review_analysis_workflow()
        )

    async def list_reviews(self, query: ReviewQuery) -> list[ReviewResponse]:
        rows = await self.commerce.list_reviews(**self._review_filters(query, include_paging=True))
        return [self._review_response(row) for row in rows]

    async def create(
        self,
        request: ReviewAnalysisCreateRequest,
        created_by: UUID,
        *,
        agent_task_id: UUID | None = None,
    ) -> ReviewAnalysisCreatedResponse:
        product = await self.commerce.get_product(request.product_id)
        if not product:
            raise ResourceNotFoundError("Product not found")
        product_site = SITE_CODES[product["site"]]
        if request.site is not None and request.site != product_site:
            raise ResourceNotFoundError("Product was not found in the requested site")
        digest = self._request_digest(request)
        existing = await self._find_idempotent(
            created_by=created_by,
            product_id=request.product_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            if existing.input_conditions.get("request_digest") != digest:
                raise IdempotencyConflictError()
            return self._created_response(existing, duplicate=True)

        if agent_task_id is None:
            agent_task = await self.tasks.create_internal_task(
                task_type=TaskType.REVIEW_ANALYSIS,
                user_input=self._safe_user_input(request),
                created_by=created_by,
            )
        else:
            agent_task = await self.tasks.get(agent_task_id, user_id=created_by)
        await self.tasks.create_steps(agent_task.id, list(STEP_NAMES))
        result = await self.analysis.add_result(
            ReviewAnalysisResult(
                created_by=created_by,
                agent_task_id=agent_task.id,
                source_product_id=request.product_id,
                site=product_site,
                requested_languages={"items": request.languages},
                input_conditions={
                    **request.model_dump(mode="json"),
                    "request_digest": digest,
                },
                status=AnalysisStatus.PENDING,
                analyzer_version="review-analysis-v1.1.0",
                source_type="simulated_experiment",
                source_snapshot_version="shopee_mock",
                summary=None,
                is_mock_data=True,
            )
        )
        return self._created_response(result, duplicate=False)

    async def run(
        self,
        analysis_id: UUID,
        user_id: UUID,
        *,
        manage_agent_task: bool = True,
    ) -> ReviewAnalysisResultResponse:
        result = await self._owned_result(analysis_id, user_id)
        if AnalysisStatus(result.status) is AnalysisStatus.SUCCEEDED:
            return await self._result_response(result)
        if AnalysisStatus(result.status) is not AnalysisStatus.PENDING:
            raise StateConflictError("Only pending review analyses can run")
        if result.agent_task_id is None:
            raise StateConflictError("Review analysis has no linked AgentTask")

        request = ReviewAnalysisCreateRequest.model_validate(
            {
                key: value
                for key, value in result.input_conditions.items()
                if key != "request_digest"
            }
        )
        steps = {
            step.step_name: step for step in await self.tasks.tasks.list_steps(result.agent_task_id)
        }
        agent_task = await self.tasks.get(result.agent_task_id, user_id=user_id)
        if manage_agent_task:
            agent_task = await self.tasks.start(result.agent_task_id)
        elif TaskStatus(agent_task.status) is not TaskStatus.RUNNING:
            raise StateConflictError("Workflow-owned review analysis task must be running")
        result.status = AnalysisStatus.RUNNING
        result.started_at = datetime.now(UTC)
        try:
            load_step = await self.tasks.start_step(
                steps["load_reviews"].id,
                input_summary={
                    "product_id": request.product_id,
                    "batch_size": request.batch_size,
                    "maximum_reviews": request.maximum_reviews,
                },
            )
            reviews = await self._load_analysis_reviews(request)
            if not reviews:
                raise ResourceNotFoundError("No reviews matched the analysis criteria")
            await self.tasks.complete_step(
                load_step.id,
                output_summary={"review_count": len(reviews)},
            )

            analysis_step = await self.tasks.start_step(
                steps["analyze_reviews"].id,
                input_summary={
                    "review_count": len(reviews),
                    "analyzer_version": result.analyzer_version,
                },
            )
            workflow_result = await self.workflow.ainvoke(
                {
                    "reviews": tuple(reviews),
                    "max_attempts": request.max_attempts,
                    "attempt_count": 0,
                    "report": None,
                }
            )
            report = ReviewAnalysisReport.model_validate(workflow_result["report"])
            agent_task.retry_count = max(int(workflow_result["attempt_count"]) - 1, 0)
            await self.tasks.complete_step(
                analysis_step.id,
                output_summary={
                    "included_count": report.quality.included_count,
                    "topic_count": len(report.topics),
                    "pain_point_count": len(report.pain_points),
                },
            )

            persist_step = await self.tasks.start_step(
                steps["persist_results"].id,
                input_summary={"evidence_review_count": len(report.judgements)},
            )
            await self._persist_report(result, report)
            await self.tasks.complete_step(
                persist_step.id,
                output_summary={
                    "evidence_count": sum(len(item.topics) for item in report.judgements)
                },
            )
            result.status = AnalysisStatus.SUCCEEDED
            result.finished_at = datetime.now(UTC)
            if manage_agent_task:
                await self.tasks.complete(
                    result.agent_task_id,
                    {
                        "analysis_id": str(result.id),
                        "included_count": report.quality.included_count,
                        "analyzer_version": report.analyzer_version,
                        "analysis_mode": "rule",
                    },
                )
        except Exception as exc:
            await self._mark_failed(
                result,
                steps,
                error_code="REVIEW_ANALYSIS_FAILED",
                error_message=self._safe_error(exc),
                manage_agent_task=manage_agent_task,
            )
            await self.session.commit()
            raise
        return await self._result_response(result)

    async def get(
        self,
        analysis_id: UUID,
        user_id: UUID,
    ) -> ReviewAnalysisResultResponse:
        return await self._result_response(await self._owned_result(analysis_id, user_id))

    async def export(self, analysis_id: UUID, user_id: UUID) -> ReviewAnalysisExportResponse:
        response = await self.get(analysis_id, user_id)
        sentiment = response.sentiment.model_dump(mode="json") if response.sentiment else {}
        topics = [item.model_dump(mode="json") for item in response.topics]
        pain_points = [item.model_dump(mode="json") for item in response.pain_points]
        lines = [
            "# SellPilot 评论分析报告",
            "",
            f"- 商品：`{response.product_id}`",
            f"- 站点：`{response.site}`",
            f"- 分析模式：`{response.analysis_mode}`",
            f"- 数据来源：`{'Mock Shopee' if response.is_mock_data else 'platform'}`",
            "",
            "## 情感概览",
            f"```json\n{json.dumps(sentiment, ensure_ascii=False, indent=2)}\n```",
            "## 主题",
            f"```json\n{json.dumps(topics, ensure_ascii=False, indent=2)}\n```",
            "## 痛点",
            f"```json\n{json.dumps(pain_points, ensure_ascii=False, indent=2)}\n```",
        ]
        return ReviewAnalysisExportResponse(
            filename=f"review-analysis-{analysis_id}.md",
            media_type="text/markdown",
            content="\n".join(lines),
        )

    async def list_evidence(
        self,
        analysis_id: UUID,
        user_id: UUID,
        *,
        page: int,
        page_size: int,
        evidence_type: str | None = None,
        label: str | None = None,
        sentiment: str | None = None,
    ) -> ReviewEvidencePage:
        await self._owned_result(analysis_id, user_id)
        rows, total = await self.analysis.list_evidence(
            analysis_id,
            page,
            page_size,
            evidence_type=evidence_type,
            label=label,
            sentiment=sentiment,
        )
        return ReviewEvidencePage(
            items=[self._evidence_response(item) for item in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def _load_analysis_reviews(
        self,
        request: ReviewAnalysisCreateRequest,
    ) -> list[ReviewInput]:
        rows: list[dict[str, object]] = []
        offset = 0
        while len(rows) < request.maximum_reviews:
            limit = min(request.batch_size, request.maximum_reviews - len(rows))
            filters = self._review_filters(
                ReviewQuery(
                    product_id=request.product_id,
                    keyword=request.keyword,
                    site=request.site,
                    min_rating=request.min_rating,
                    max_rating=request.max_rating,
                    created_from=request.created_from,
                    created_to=request.created_to,
                    offset=offset,
                    limit=limit,
                ),
                include_paging=True,
            )
            if request.languages:
                filters["languages"] = request.languages
            batch = await self.commerce.list_reviews(**filters)
            if not batch:
                break
            rows.extend(batch)
            offset += len(batch)
            if len(batch) < limit:
                break
        reviews = [self._domain_review(row) for row in rows]
        missing = [
            (review.review_id, review.content)
            for review in reviews
            if not review.translated_content
            and (review.declared_language or "").lower() not in {"en", "english"}
        ]
        translations: dict[str, str] = {}
        for offset in range(0, len(missing), 30):
            translations.update(
                await translate_review_batch(self.settings, missing[offset : offset + 30])
            )
        if translations:
            reviews = [
                review.model_copy(
                    update={
                        "translated_content": translations.get(
                            review.review_id, review.translated_content
                        )
                    }
                )
                for review in reviews
            ]
        return reviews

    async def _persist_report(
        self,
        result: ReviewAnalysisResult,
        report: ReviewAnalysisReport,
    ) -> None:
        result.summary = {
            **report.model_dump(mode="json"),
            "analysis_mode": (
                "validated_model"
                if self.settings.content_model_provider == "aliyun_bailian"
                else "rule"
            ),
            "prompt_version": "review-translation-v1"
            if self.settings.content_model_provider == "aliyun_bailian"
            else None,
            "model_version": self.settings.bailian_model
            if self.settings.content_model_provider == "aliyun_bailian"
            else None,
        }
        evidence_items = []
        for judgement in report.judgements:
            for topic in judgement.topics:
                evidence_items.append(
                    ReviewAnalysisEvidence(
                        result_id=result.id,
                        source_review_id=judgement.review_id,
                        source_product_id=judgement.product_id,
                        source_type=result.source_type,
                        is_mock_data=result.is_mock_data,
                        language=judgement.detected_language,
                        rating=judgement.rating,
                        evidence_type="topic",
                        label=topic,
                        sentiment=judgement.sentiment,
                        issue_type=topic,
                        excerpt=judgement.original_content,
                        translated_excerpt=judgement.translated_content,
                        source_created_at=judgement.source_created_at,
                        confidence=judgement.confidence,
                        evidence_metadata={
                            "origin": judgement.origin,
                            "translation_status": judgement.translation_status,
                            "quality_flags": list(judgement.quality_flags),
                        },
                    )
                )
        await self.analysis.add_evidence(evidence_items)

    async def _mark_failed(
        self,
        result: ReviewAnalysisResult,
        steps: dict[str, object],
        *,
        error_code: str,
        error_message: str,
        manage_agent_task: bool,
    ) -> None:
        result.status = AnalysisStatus.FAILED
        result.error_message = error_message
        result.finished_at = datetime.now(UTC)
        if result.agent_task_id is not None:
            task = await self.tasks.get(result.agent_task_id)
            if TaskStatus(task.status) is TaskStatus.RUNNING:
                for step in steps.values():
                    if str(step.status) in {"pending", "running"}:
                        await self.tasks.fail_step(step.id, error_message)
                        break
                task.retry_count = max(
                    int(result.input_conditions.get("max_attempts", 1)) - 1,
                    0,
                )
                if manage_agent_task:
                    await self.tasks.fail(result.agent_task_id, error_code, error_message)

    async def _owned_result(
        self,
        analysis_id: UUID,
        user_id: UUID,
    ) -> ReviewAnalysisResult:
        result = await self.analysis.get_result(analysis_id)
        if result is None or result.created_by != user_id:
            raise ResourceNotFoundError("Review analysis not found")
        return result

    async def _find_idempotent(
        self,
        *,
        created_by: UUID,
        product_id: str,
        idempotency_key: str,
    ) -> ReviewAnalysisResult | None:
        return await self.analysis.find_by_idempotency_key(
            created_by=created_by,
            source_product_id=product_id,
            idempotency_key=idempotency_key,
        )

    @staticmethod
    def _request_digest(request: ReviewAnalysisCreateRequest) -> str:
        payload = request.model_dump(mode="json", exclude={"idempotency_key"})
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _safe_user_input(request: ReviewAnalysisCreateRequest) -> str:
        return json.dumps(
            {
                "product_id": request.product_id,
                "site": request.site,
                "languages": request.languages,
                "rating_range": [request.min_rating, request.max_rating],
                "time_range": [request.created_from, request.created_to],
                "maximum_reviews": request.maximum_reviews,
            },
            default=str,
            ensure_ascii=False,
            sort_keys=True,
        )

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        if isinstance(exc, ResourceNotFoundError):
            return exc.message
        return f"Review analysis failed ({type(exc).__name__})"

    @staticmethod
    def _review_filters(query: ReviewQuery, *, include_paging: bool) -> dict[str, object]:
        filters: dict[str, object] = {
            "product_id": query.product_id,
            "keyword": query.keyword,
            "site": SITE_NAMES[query.site] if query.site else None,
            "language": query.language,
            "min_rating": query.min_rating,
            "max_rating": query.max_rating,
            "created_from": query.created_from,
            "created_to": query.created_to,
        }
        if include_paging:
            filters.update(offset=query.offset, limit=query.limit)
        return {key: value for key, value in filters.items() if value is not None}

    @staticmethod
    def _review_response(row: dict[str, object]) -> ReviewResponse:
        sentiment, topics = classify_review_preview(ReviewAnalysisService._domain_review(row))
        primary_topic = next(
            (
                topic
                for topic in topics
                if topic not in {ReviewTopic.NO_CLEAR_ISSUE, ReviewTopic.OTHER}
            ),
            topics[0],
        )
        return ReviewResponse(
            review_id=row["review_id"],
            product_id=row["product_id"],
            site=SITE_CODES[row["site"]],
            rating=row["rating"],
            content=row["content"],
            translated_content=row["translated_content"],
            language=row["language"],
            sentiment_hint=sentiment,
            issue_type=primary_topic,
            created_at=row["created_at"],
            source_type=row["source_type"],
            is_mock_data=row["is_mock_data"],
        )

    @classmethod
    def _domain_review(cls, row: dict[str, object]) -> ReviewInput:
        return ReviewInput(
            review_id=row["review_id"],
            product_id=row["product_id"],
            site=SITE_CODES[row["site"]],
            rating=row["rating"],
            content=row["content"],
            translated_content=row["translated_content"],
            declared_language=row["language"],
            source_created_at=row["created_at"],
            source=SourceMetadata(
                source_type=DataSource.MOCK,
                source_name=row["source_type"],
                source_reference=row["product_id"],
                is_mock=row["is_mock_data"],
            ),
            source_sentiment_hint=row["sentiment_hint"],
            source_issue_hint=row["issue_type"],
        )

    @staticmethod
    def _created_response(
        result: ReviewAnalysisResult,
        *,
        duplicate: bool,
    ) -> ReviewAnalysisCreatedResponse:
        return ReviewAnalysisCreatedResponse(
            analysis_id=result.id,
            agent_task_id=result.agent_task_id,
            status=AnalysisStatus(result.status),
            duplicate=duplicate,
            analyzer_version=result.analyzer_version,
            analysis_mode="rule",
            prompt_version=None,
            model_version=None,
            is_mock_data=result.is_mock_data,
        )

    async def _result_response(
        self,
        result: ReviewAnalysisResult,
    ) -> ReviewAnalysisResultResponse:
        summary = result.summary or {}
        task = await self.tasks.get(result.agent_task_id) if result.agent_task_id else None
        step_rows = (
            await self.tasks.tasks.list_steps(result.agent_task_id) if result.agent_task_id else []
        )
        completed_steps = sum(str(step.status) == "succeeded" for step in step_rows)
        progress = (
            100
            if AnalysisStatus(result.status) is AnalysisStatus.SUCCEEDED
            else round(completed_steps / len(STEP_NAMES) * 100)
        )
        return ReviewAnalysisResultResponse(
            analysis_id=result.id,
            agent_task_id=result.agent_task_id,
            product_id=result.source_product_id,
            site=SiteCode(result.site),
            status=AnalysisStatus(result.status),
            progress=progress,
            current_step=task.current_step if task else None,
            steps=tuple(
                {
                    "step_name": step.step_name,
                    "status": step.status,
                    "input_summary": step.input_summary,
                    "output_summary": step.output_summary,
                    "error_message": step.error_message,
                    "started_at": step.started_at,
                    "finished_at": step.finished_at,
                }
                for step in step_rows
            ),
            analyzer_version=result.analyzer_version,
            analysis_mode=summary.get("analysis_mode", "rule"),
            prompt_version=summary.get("prompt_version"),
            model_version=summary.get("model_version"),
            quality=summary.get("quality"),
            sentiment=summary.get("sentiment"),
            topics=summary.get("topics", ()),
            pain_points=summary.get("pain_points", ()),
            keywords=summary.get("keywords", ()),
            trends=summary.get("trends", ()),
            judgements=summary.get("judgements", ()),
            error_message=result.error_message,
            is_mock_data=result.is_mock_data,
            started_at=result.started_at,
            finished_at=result.finished_at,
        )

    @staticmethod
    def _evidence_response(item: ReviewAnalysisEvidence) -> ReviewEvidenceResponse:
        return ReviewEvidenceResponse(
            id=item.id,
            review_id=item.source_review_id,
            product_id=item.source_product_id,
            language=item.language,
            rating=item.rating,
            evidence_type=item.evidence_type,
            label=item.label,
            sentiment=item.sentiment,
            issue_type=item.issue_type,
            original_content=item.excerpt,
            translated_content=item.translated_excerpt,
            source_created_at=item.source_created_at,
            confidence=item.confidence,
            metadata=item.evidence_metadata,
            is_mock_data=item.is_mock_data,
        )
