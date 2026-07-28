import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.core.enums import AnalysisStatus, CurrencyCode, DataSource, SiteCode, TaskType
from sellpilot.core.exceptions import ParameterError, ResourceNotFoundError
from sellpilot.db.models.analysis import ProductSelectionResult, ProductSelectionTask
from sellpilot.domain.selection.models import (
    SelectionCandidate,
    SelectionCriteria,
    SelectionFormulaConfig,
    SelectionMetric,
)
from sellpilot.domain.selection.scoring import DEFAULT_SELECTION_CONFIG, score_candidates
from sellpilot.repositories.analysis import SelectionRepository
from sellpilot.repositories.selection_market import SelectionMarketRepository
from sellpilot.schemas.common import SourceMetadata
from sellpilot.schemas.selection import (
    SelectionAnalysisRequest,
    SelectionAnalysisResponse,
    SelectionCandidateQuery,
    SelectionCandidateResponse,
    SelectionExportResponse,
    SelectionResultResponse,
    SelectionTaskResponse,
)
from sellpilot.services.task import TaskService
from sellpilot.workflows.selection import (
    ExplanationGenerator,
    SelectionExplanation,
    build_selection_explanation_workflow,
)

SITE_CODES = {
    "Singapore": SiteCode.SG,
    "Malaysia": SiteCode.MY,
    "Philippines": SiteCode.PH,
    "Thailand": SiteCode.TH,
    "Vietnam": SiteCode.VN,
    "Indonesia": SiteCode.ID,
}

SELECTION_CONFIGS = {
    "balanced": DEFAULT_SELECTION_CONFIG,
    "conservative": SelectionFormulaConfig(
        version="selection-v1.0.0-conservative",
        weights={
            SelectionMetric.DEMAND: Decimal("0.18"),
            SelectionMetric.COMPETITION: Decimal("0.12"),
            SelectionMetric.PROFITABILITY: Decimal("0.30"),
            SelectionMetric.REVIEW_QUALITY: Decimal("0.10"),
            SelectionMetric.LOGISTICS: Decimal("0.15"),
            SelectionMetric.AFTER_SALES: Decimal("0.10"),
            SelectionMetric.FACTORY_FIT: Decimal("0.05"),
        },
    ),
    "growth": SelectionFormulaConfig(
        version="selection-v1.0.0-growth",
        weights={
            SelectionMetric.DEMAND: Decimal("0.35"),
            SelectionMetric.COMPETITION: Decimal("0.18"),
            SelectionMetric.PROFITABILITY: Decimal("0.20"),
            SelectionMetric.REVIEW_QUALITY: Decimal("0.12"),
            SelectionMetric.LOGISTICS: Decimal("0.05"),
            SelectionMetric.AFTER_SALES: Decimal("0.05"),
            SelectionMetric.FACTORY_FIT: Decimal("0.05"),
        },
    ),
}


class SelectionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        explanation_generator: ExplanationGenerator | None = None,
    ) -> None:
        self.session = session
        self.market = SelectionMarketRepository(session)
        self.selection = SelectionRepository(session)
        self.tasks = TaskService(session)
        self.explanation_workflow = build_selection_explanation_workflow(explanation_generator)

    async def list_candidates(
        self, query: SelectionCandidateQuery
    ) -> list[SelectionCandidateResponse]:
        return [
            self._candidate_response(product, trend)
            for product, trend in await self.market.list_candidates(query)
        ]

    async def analyze(
        self, request: SelectionAnalysisRequest, created_by: UUID
    ) -> SelectionAnalysisResponse:
        formula_config = SELECTION_CONFIGS[request.risk_preference]
        agent_task = await self.tasks.create_internal_task(
            task_type=TaskType.SELECTION,
            user_input=request.model_dump_json(),
            created_by=created_by,
        )
        await self.tasks.start(agent_task.id)
        selection_task = await self.selection.add_task(
            ProductSelectionTask(
                created_by=created_by,
                agent_task_id=agent_task.id,
                status=AnalysisStatus.RUNNING,
                criteria=request.model_dump(mode="json"),
                algorithm_version=formula_config.version,
                source_type="simulated_experiment",
                source_snapshot_version="shopee_mock",
                is_mock_data=True,
                started_at=datetime.now(UTC),
            )
        )
        query_fields = SelectionCandidateQuery.model_fields
        rows = await self.market.list_candidates(
            SelectionCandidateQuery.model_validate(request.model_dump(include=set(query_fields)))
        )
        if not rows:
            selection_task.status = AnalysisStatus.FAILED
            selection_task.error_message = "No candidates matched the criteria"
            selection_task.finished_at = datetime.now(UTC)
            await self.tasks.fail(
                agent_task.id, "SELECTION_NO_CANDIDATES", selection_task.error_message
            )
            raise ResourceNotFoundError("No selection candidates matched the criteria")
        candidates = [self._domain_candidate(product, trend, request) for product, trend in rows]
        batch = score_candidates(
            candidates,
            SelectionCriteria(
                minimum_profit=request.minimum_profit,
                minimum_margin=request.minimum_margin,
            ),
            formula_config,
        )
        title_by_id = {product.external_id: product.title for product, _ in rows}
        persisted: list[ProductSelectionResult] = []
        responses: list[SelectionResultResponse] = []
        generation_modes: set[str] = set()
        for scored in batch.ranked:
            payload = scored.model_dump(mode="json")
            workflow_result = await self.explanation_workflow.ainvoke(
                {"score": payload, "explanation": None}
            )
            explanation = SelectionExplanation.model_validate(workflow_result["explanation"])
            generation_modes.add(explanation.generation_mode)
            model = ProductSelectionResult(
                task_id=selection_task.id,
                source_product_id=scored.product_id,
                site=scored.site,
                currency=scored.currency,
                source_type="simulated_experiment",
                is_mock_data=True,
                rank=scored.rank,
                total_score=scored.total_score,
                metric_breakdown=payload["metrics"],
                recommendation_reason=explanation.model_dump_json(),
                risk_warnings={"items": list(scored.risk_warnings)},
                data_completeness=scored.data_completeness,
                data_sources=scored.source.model_dump(mode="json"),
                evidence={"explanation": explanation.model_dump(mode="json")},
                source_snapshot={
                    "title": title_by_id[scored.product_id],
                    "profit": payload["profit"],
                    "formula_version": scored.formula_version,
                },
            )
            persisted.append(model)
        await self.selection.add_results(persisted)
        for model in persisted:
            responses.append(self._result_response(model))
        selection_task.status = AnalysisStatus.SUCCEEDED
        selection_task.finished_at = datetime.now(UTC)
        await self.tasks.complete(
            agent_task.id,
            {
                "selection_task_id": str(selection_task.id),
                "ranked_count": len(responses),
                "excluded_count": len(batch.excluded),
            },
        )
        return SelectionAnalysisResponse(
            task_id=selection_task.id,
            agent_task_id=agent_task.id,
            status=AnalysisStatus.SUCCEEDED,
            formula_version=batch.formula_version,
            generation_mode=(
                "validated_generator"
                if generation_modes == {"validated_generator"}
                else "rule_template"
            ),
            total_candidates=len(candidates),
            ranked_count=len(responses),
            excluded_count=len(batch.excluded),
            results=responses,
            excluded=[item.model_dump(mode="json") for item in batch.excluded],
            is_mock_data=True,
        )

    async def get_task(self, task_id: UUID, user_id: UUID) -> SelectionTaskResponse:
        task = await self.selection.get_task(task_id)
        if task is None or task.created_by != user_id:
            raise ResourceNotFoundError("Selection task not found")
        results, _ = await self.selection.list_results(task_id, 1, 100)
        return SelectionTaskResponse(
            task_id=task.id,
            agent_task_id=task.agent_task_id,
            status=AnalysisStatus(task.status),
            criteria=task.criteria,
            formula_version=task.algorithm_version,
            is_mock_data=task.is_mock_data,
            results=[self._result_response(item) for item in results],
        )

    async def compare(
        self, task_id: UUID, product_ids: list[str], user_id: UUID
    ) -> list[SelectionResultResponse]:
        if len(product_ids) < 2 or len(product_ids) > 10:
            raise ParameterError("compare requires between 2 and 10 product_ids")
        if len(product_ids) != len(set(product_ids)):
            raise ParameterError("compare product_ids must be unique")
        task = await self.get_task(task_id, user_id)
        selected = [item for item in task.results if item.product_id in set(product_ids)]
        if len(selected) != len(set(product_ids)):
            raise ResourceNotFoundError("One or more comparison products were not found")
        return selected

    async def export(self, task_id: UUID, user_id: UUID) -> SelectionExportResponse:
        task = await self.get_task(task_id, user_id)
        canonical = json.dumps(
            task.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return SelectionExportResponse(
            filename=f"selection-{task_id}.json",
            content_type="application/json",
            checksum_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            task=task,
        )

    @staticmethod
    def _candidate_response(product, trend) -> SelectionCandidateResponse:
        return SelectionCandidateResponse(
            product_id=product.external_id,
            title=product.title,
            category_id=product.category_external_id,
            category_name=product.category_name,
            site=SITE_CODES[product.site],
            currency=CurrencyCode(product.currency),
            price=product.price,
            cost=product.cost,
            shipping_cost=product.shipping_cost,
            sales_count=product.sales_count,
            rating=product.rating,
            review_count=product.review_count,
            search_index=trend.search_index if trend else None,
            sales_index=trend.sales_index if trend else None,
            competition_index=trend.competition_index if trend else None,
            growth_rate=trend.growth_rate if trend else None,
            source_name=product.source_type,
            is_mock_data=product.is_mock_data,
        )

    @staticmethod
    def _domain_candidate(product, trend, request) -> SelectionCandidate:
        return SelectionCandidate(
            product_id=product.external_id,
            site=SITE_CODES[product.site],
            currency=CurrencyCode(product.currency),
            source=SourceMetadata(
                source_type=DataSource.MOCK,
                source_name=product.source_type,
                source_reference=product.external_id,
                is_mock=True,
                collected_at=product.collected_at,
            ),
            price=product.price,
            cost=request.cost_override if request.cost_override is not None else product.cost,
            shipping_cost=request.shipping_cost_override
            if request.shipping_cost_override is not None
            else product.shipping_cost,
            platform_fee_rate=request.platform_fee_rate,
            other_costs=request.other_costs,
            sales_count=product.sales_count,
            search_index=trend.search_index if trend else None,
            sales_index=trend.sales_index if trend else None,
            growth_rate=trend.growth_rate if trend else None,
            competition_index=trend.competition_index if trend else None,
            rating=product.rating,
            review_count=product.review_count,
        )

    @staticmethod
    def _result_response(model: ProductSelectionResult) -> SelectionResultResponse:
        explanation = json.loads(model.recommendation_reason)
        snapshot = model.source_snapshot or {}
        return SelectionResultResponse(
            id=model.id,
            product_id=model.source_product_id,
            title=snapshot.get("title"),
            rank=model.rank,
            total_score=model.total_score,
            data_completeness=model.data_completeness,
            currency=CurrencyCode(model.currency),
            site=SiteCode(model.site),
            profit=snapshot.get("profit", {}),
            metrics=model.metric_breakdown,
            explanation=explanation,
            risk_warnings=list(model.risk_warnings.get("items", [])),
            evidence=model.evidence,
            is_mock_data=model.is_mock_data,
        )
