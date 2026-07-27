from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import delete, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sellpilot.db.models.analysis import (
    ProductImprovementReport,
    ProductImprovementSuggestion,
    ProductSelectionResult,
    ProductSelectionTask,
    ReviewAnalysisEvidence,
    ReviewAnalysisResult,
)
from sellpilot.db.models.content import (
    GeneratedReport,
    ProductContent,
    ProductContentVersion,
)
from sellpilot.db.models.model_management import (
    ModelInvocation,
    PromptTemplate,
    PromptVersion,
)
from sellpilot.db.models.user import User
from sellpilot.repositories.analysis import (
    ImprovementRepository,
    ReviewAnalysisRepository,
    SelectionRepository,
)
from sellpilot.repositories.content import (
    GeneratedReportRepository,
    ProductContentRepository,
)
from sellpilot.repositories.model_management import (
    ModelInvocationRepository,
    PromptRepository,
)


@pytest.mark.asyncio
async def test_selection_repository_persists_filters_and_paginates(
    session: AsyncSession,
    admin_user: User,
) -> None:
    repository = SelectionRepository(session)
    completed_task = await repository.add_task(
        ProductSelectionTask(
            created_by=admin_user.id,
            status="SUCCEEDED",
            criteria={"sites": ["Singapore"], "minimum_margin": "0.20"},
            algorithm_version="selection-v1",
            source_type="simulated_experiment",
            source_snapshot_version="mock-20260727",
            is_mock_data=True,
        )
    )
    await repository.add_task(
        ProductSelectionTask(
            created_by=admin_user.id,
            status="FAILED",
            criteria={"sites": ["Malaysia"]},
            algorithm_version="selection-v1",
            source_type="simulated_experiment",
            is_mock_data=True,
            error_message="synthetic test failure",
        )
    )
    await repository.add_results(
        [
            ProductSelectionResult(
                task_id=completed_task.id,
                source_product_id="PROD0001",
                site="Singapore",
                currency="SGD",
                source_type="simulated_experiment",
                is_mock_data=True,
                rank=1,
                total_score=Decimal("88.5000"),
                metric_breakdown={"margin": "92.0000"},
                recommendation_reason="Strong synthetic score.",
                risk_warnings={"values": ["Synthetic logistics risk"]},
                data_completeness=Decimal("0.9500"),
                data_sources={"type": "simulated_experiment"},
                evidence={"trend_ids": ["TREND0000001"]},
            ),
            ProductSelectionResult(
                task_id=completed_task.id,
                source_product_id="PROD0002",
                site="Singapore",
                currency="SGD",
                source_type="simulated_experiment",
                is_mock_data=True,
                rank=2,
                total_score=Decimal("81.2500"),
                metric_breakdown={"margin": "84.0000"},
                recommendation_reason="Good synthetic score.",
                risk_warnings={"values": []},
                data_completeness=Decimal("0.9000"),
                data_sources={"type": "simulated_experiment"},
                evidence={"trend_ids": ["TREND0000002"]},
            ),
        ]
    )

    succeeded, succeeded_total = await repository.list_tasks(
        1,
        10,
        status="SUCCEEDED",
    )
    first_page, result_total = await repository.list_results(completed_task.id, 1, 1)
    second_page, _ = await repository.list_results(completed_task.id, 2, 1)

    assert succeeded_total == 1
    assert [task.id for task in succeeded] == [completed_task.id]
    assert result_total == 2
    assert [item.rank for item in first_page] == [1]
    assert [item.rank for item in second_page] == [2]


@pytest.mark.asyncio
async def test_selection_result_constraints_reject_duplicate_product(
    session: AsyncSession,
    admin_user: User,
) -> None:
    repository = SelectionRepository(session)
    task = await repository.add_task(
        ProductSelectionTask(
            created_by=admin_user.id,
            criteria={"sites": ["Singapore"]},
            algorithm_version="selection-v1",
            source_type="simulated_experiment",
            is_mock_data=True,
        )
    )
    result_values = {
        "task_id": task.id,
        "source_product_id": "PROD0001",
        "site": "Singapore",
        "currency": "SGD",
        "source_type": "simulated_experiment",
        "is_mock_data": True,
        "rank": 1,
        "total_score": Decimal("75.0000"),
        "metric_breakdown": {"margin": "75.0000"},
        "recommendation_reason": "Synthetic recommendation.",
        "risk_warnings": {"values": []},
        "data_completeness": Decimal("1.0000"),
        "data_sources": {"type": "simulated_experiment"},
        "evidence": {"trend_ids": []},
    }
    await repository.add_results([ProductSelectionResult(**result_values)])

    with pytest.raises(IntegrityError):
        await repository.add_results([ProductSelectionResult(**result_values)])


@pytest.mark.asyncio
async def test_selection_result_constraints_reject_duplicate_rank(
    session: AsyncSession,
    admin_user: User,
) -> None:
    repository = SelectionRepository(session)
    task = await repository.add_task(
        ProductSelectionTask(
            created_by=admin_user.id,
            criteria={"sites": ["Singapore"]},
            algorithm_version="selection-v1",
            source_type="simulated_experiment",
            is_mock_data=True,
        )
    )
    shared_values = {
        "task_id": task.id,
        "site": "Singapore",
        "currency": "SGD",
        "source_type": "simulated_experiment",
        "is_mock_data": True,
        "rank": 1,
        "total_score": Decimal("75.0000"),
        "metric_breakdown": {"margin": "75.0000"},
        "recommendation_reason": "Synthetic recommendation.",
        "risk_warnings": {"values": []},
        "data_completeness": Decimal("1.0000"),
        "data_sources": {"type": "simulated_experiment"},
        "evidence": {"trend_ids": []},
    }
    await repository.add_results(
        [ProductSelectionResult(source_product_id="PROD0001", **shared_values)]
    )

    with pytest.raises(IntegrityError):
        await repository.add_results(
            [ProductSelectionResult(source_product_id="PROD0002", **shared_values)]
        )


@pytest.mark.parametrize(
    ("total_score", "data_completeness"),
    [
        (Decimal("100.0001"), Decimal("1.0000")),
        (Decimal("75.0000"), Decimal("1.0001")),
    ],
)
@pytest.mark.asyncio
async def test_selection_result_rejects_out_of_range_metrics(
    session: AsyncSession,
    admin_user: User,
    total_score: Decimal,
    data_completeness: Decimal,
) -> None:
    repository = SelectionRepository(session)
    task = await repository.add_task(
        ProductSelectionTask(
            created_by=admin_user.id,
            criteria={"sites": ["Singapore"]},
            algorithm_version="selection-v1",
            source_type="simulated_experiment",
            is_mock_data=True,
        )
    )

    with pytest.raises(IntegrityError):
        await repository.add_results(
            [
                ProductSelectionResult(
                    task_id=task.id,
                    source_product_id="PROD0001",
                    site="Singapore",
                    currency="SGD",
                    source_type="simulated_experiment",
                    is_mock_data=True,
                    rank=1,
                    total_score=total_score,
                    metric_breakdown={"margin": "75.0000"},
                    recommendation_reason="Synthetic recommendation.",
                    risk_warnings={"values": []},
                    data_completeness=data_completeness,
                    data_sources={"type": "simulated_experiment"},
                    evidence={"trend_ids": []},
                )
            ]
        )


@pytest.mark.asyncio
async def test_review_and_improvement_repositories_preserve_evidence_chain(
    session: AsyncSession,
    admin_user: User,
) -> None:
    review_repository = ReviewAnalysisRepository(session)
    improvement_repository = ImprovementRepository(session)
    analysis_result = await review_repository.add_result(
        ReviewAnalysisResult(
            created_by=admin_user.id,
            source_product_id="PROD0036",
            site="Indonesia",
            requested_languages={"values": ["Indonesian", "Chinese"]},
            input_conditions={"date_range": "all"},
            analyzer_version="review-v1",
            source_type="simulated_experiment",
            source_snapshot_version="mock-20260727",
            status="SUCCEEDED",
            summary={"negative_ratio": "0.1250"},
            is_mock_data=True,
        )
    )
    evidence = await review_repository.add_evidence(
        [
            ReviewAnalysisEvidence(
                result_id=analysis_result.id,
                source_review_id="REV000001",
                source_product_id="PROD0036",
                source_type="simulated_experiment",
                is_mock_data=True,
                language="Indonesian",
                rating=5,
                evidence_type="TOPIC",
                label="shipping",
                sentiment="positive",
                excerpt="Synthetic review excerpt.",
                translated_excerpt="合成评论摘录。",
                source_created_at=datetime(2026, 2, 15, 15, 43, tzinfo=UTC),
                confidence=Decimal("0.9200"),
                evidence_metadata={"is_mock_data": True},
            )
        ]
    )
    report = await improvement_repository.add_report(
        ProductImprovementReport(
            review_analysis_result_id=analysis_result.id,
            source_product_id="PROD0036",
            version=1,
            algorithm_version="improvement-v1",
            status="READY",
            source_type="simulated_experiment",
            is_mock_data=True,
            data_sources={"review_ids": ["REV000001"]},
            input_conditions={"minimum_frequency": "0.1000"},
            summary={"focus": "packaging"},
            created_by=admin_user.id,
        )
    )
    suggestions = await improvement_repository.add_suggestions(
        [
            ProductImprovementSuggestion(
                report_id=report.id,
                suggestion_key="packaging-protection",
                category="PACKAGING",
                title="Improve protective packaging",
                description="Use a synthetic packaging improvement for testing.",
                priority=1,
                severity=Decimal("0.8000"),
                confidence=Decimal("0.9000"),
                evidence_count=1,
                frequency_rate=Decimal("0.1250"),
                evidence_review_ids={"values": [evidence[0].source_review_id]},
                expected_impact={"return_rate": "decrease"},
            )
        ]
    )

    evidence_page, evidence_total = await review_repository.list_evidence(
        analysis_result.id,
        1,
        10,
        evidence_type="TOPIC",
    )
    report_page, report_total = await improvement_repository.list_reports(
        1,
        10,
        source_product_id="PROD0036",
    )
    stored_suggestions, suggestion_total = await improvement_repository.list_suggestions(
        report.id,
        1,
        10,
    )

    assert evidence_total == 1
    assert evidence_page[0].source_review_id == "REV000001"
    assert report_total == 1
    assert report_page[0].review_analysis_result_id == analysis_result.id
    assert suggestion_total == 1
    assert [item.id for item in stored_suggestions] == [suggestions[0].id]
    assert suggestions[0].status == "PROPOSED"


@pytest.mark.parametrize(
    ("rating", "confidence"),
    [
        (0, Decimal("0.5000")),
        (5, Decimal("1.0001")),
    ],
)
@pytest.mark.asyncio
async def test_review_evidence_rejects_out_of_range_values(
    session: AsyncSession,
    admin_user: User,
    rating: int,
    confidence: Decimal,
) -> None:
    repository = ReviewAnalysisRepository(session)
    analysis_result = await repository.add_result(
        ReviewAnalysisResult(
            created_by=admin_user.id,
            source_product_id="PROD0036",
            site="Indonesia",
            requested_languages={"values": ["Indonesian"]},
            input_conditions={"date_range": "all"},
            analyzer_version="review-v1",
            source_type="simulated_experiment",
            is_mock_data=True,
        )
    )

    with pytest.raises(IntegrityError):
        await repository.add_evidence(
            [
                ReviewAnalysisEvidence(
                    result_id=analysis_result.id,
                    source_review_id="REV000001",
                    source_product_id="PROD0036",
                    source_type="simulated_experiment",
                    is_mock_data=True,
                    language="Indonesian",
                    rating=rating,
                    evidence_type="TOPIC",
                    label="shipping",
                    excerpt="Synthetic review excerpt.",
                    source_created_at=datetime(2026, 2, 15, 15, 43, tzinfo=UTC),
                    confidence=confidence,
                )
            ]
        )


@pytest.mark.asyncio
async def test_improvement_suggestion_rejects_invalid_frequency(
    session: AsyncSession,
    admin_user: User,
) -> None:
    review_repository = ReviewAnalysisRepository(session)
    improvement_repository = ImprovementRepository(session)
    analysis_result = await review_repository.add_result(
        ReviewAnalysisResult(
            created_by=admin_user.id,
            source_product_id="PROD0036",
            site="Indonesia",
            requested_languages={"values": ["Indonesian"]},
            input_conditions={"date_range": "all"},
            analyzer_version="review-v1",
            source_type="simulated_experiment",
            is_mock_data=True,
        )
    )
    report = await improvement_repository.add_report(
        ProductImprovementReport(
            review_analysis_result_id=analysis_result.id,
            source_product_id="PROD0036",
            version=1,
            algorithm_version="improvement-v1",
            source_type="simulated_experiment",
            is_mock_data=True,
            data_sources={"review_ids": []},
            input_conditions={"minimum_frequency": "0.1000"},
            summary={"focus": "packaging"},
            created_by=admin_user.id,
        )
    )

    with pytest.raises(IntegrityError):
        await improvement_repository.add_suggestions(
            [
                ProductImprovementSuggestion(
                    report_id=report.id,
                    suggestion_key="invalid-frequency",
                    category="PACKAGING",
                    title="Invalid synthetic suggestion",
                    description="Constraint validation input.",
                    priority=1,
                    severity=Decimal("0.8000"),
                    confidence=Decimal("0.9000"),
                    evidence_count=1,
                    frequency_rate=Decimal("1.0001"),
                    evidence_review_ids={"values": ["REV000001"]},
                )
            ]
        )


@pytest.mark.asyncio
async def test_selection_evidence_chain_restricts_parent_delete(
    session: AsyncSession,
    admin_user: User,
) -> None:
    await session.execute(text("PRAGMA foreign_keys = ON"))
    repository = SelectionRepository(session)
    task = await repository.add_task(
        ProductSelectionTask(
            created_by=admin_user.id,
            criteria={"sites": ["Singapore"]},
            algorithm_version="selection-v1",
            source_type="simulated_experiment",
            is_mock_data=True,
        )
    )
    await repository.add_results(
        [
            ProductSelectionResult(
                task_id=task.id,
                source_product_id="PROD0001",
                site="Singapore",
                currency="SGD",
                source_type="simulated_experiment",
                is_mock_data=True,
                rank=1,
                total_score=Decimal("75.0000"),
                metric_breakdown={"margin": "75.0000"},
                recommendation_reason="Synthetic recommendation.",
                risk_warnings={"values": []},
                data_completeness=Decimal("1.0000"),
                data_sources={"type": "simulated_experiment"},
                evidence={"trend_ids": []},
            )
        ]
    )

    with pytest.raises(IntegrityError):
        await session.execute(
            delete(ProductSelectionTask).where(ProductSelectionTask.id == task.id)
        )


@pytest.mark.asyncio
async def test_model_invocation_rejects_negative_cost(
    session: AsyncSession,
    admin_user: User,
) -> None:
    repository = ModelInvocationRepository(session)

    with pytest.raises(IntegrityError):
        await repository.add(
            ModelInvocation(
                provider="fake",
                model_name="fake-structured-model",
                status="SUCCEEDED",
                input_digest="d" * 64,
                model_parameters={"temperature": 0},
                timeout_ms=30000,
                retry_count=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=0,
                estimated_cost=Decimal("-0.000001"),
                cost_currency="USD",
                created_by=admin_user.id,
            )
        )


@pytest.mark.parametrize(
    ("timeout_ms", "retry_count"),
    [
        (0, 0),
        (30000, -1),
    ],
)
@pytest.mark.asyncio
async def test_model_invocation_rejects_invalid_execution_limits(
    session: AsyncSession,
    admin_user: User,
    timeout_ms: int,
    retry_count: int,
) -> None:
    repository = ModelInvocationRepository(session)

    with pytest.raises(IntegrityError):
        await repository.add(
            ModelInvocation(
                provider="fake",
                model_name="fake-structured-model",
                status="FAILED",
                input_digest="e" * 64,
                model_parameters={"temperature": 0},
                timeout_ms=timeout_ms,
                retry_count=retry_count,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=0,
                estimated_cost=Decimal("0.000000"),
                cost_currency="USD",
                created_by=admin_user.id,
            )
        )


@pytest.mark.asyncio
async def test_prompt_content_invocation_and_report_repositories(
    session: AsyncSession,
    admin_user: User,
) -> None:
    prompt_repository = PromptRepository(session)
    invocation_repository = ModelInvocationRepository(session)
    content_repository = ProductContentRepository(session)
    report_repository = GeneratedReportRepository(session)

    template = await prompt_repository.add_template(
        PromptTemplate(
            key="listing-localization",
            name="Listing localization",
            purpose="Generate synthetic localized listing content.",
            task_type="LISTING_GENERATION",
            language="English",
            created_by=admin_user.id,
        )
    )
    prompt_version = await prompt_repository.add_version(
        PromptVersion(
            template_id=template.id,
            version=1,
            content="Generate structured synthetic listing content.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            model_config={"temperature": 0},
            change_summary="Initial synthetic prompt version.",
            checksum="a" * 64,
            created_by=admin_user.id,
        )
    )
    invocation = await invocation_repository.add(
        ModelInvocation(
            prompt_version_id=prompt_version.id,
            provider="fake",
            model_name="fake-structured-model",
            status="SUCCEEDED",
            input_digest="b" * 64,
            input_summary={"product_id": "PROD0001"},
            output_summary={"validated": True},
            model_parameters={"temperature": 0},
            timeout_ms=30000,
            retry_count=0,
            prompt_tokens=20,
            completion_tokens=30,
            total_tokens=50,
            duration_ms=15,
            estimated_cost=Decimal("0.000000"),
            cost_currency="USD",
            created_by=admin_user.id,
        )
    )
    content = await content_repository.add_content(
        ProductContent(
            source_product_id="PROD0001",
            site="Singapore",
            target_language="English",
            source_type="simulated_experiment",
            source_snapshot_version="mock-20260727",
            source_facts={"currency": "SGD", "is_mock_data": True},
            is_mock_data=True,
            created_by=admin_user.id,
        )
    )
    version = await content_repository.add_version(
        ProductContentVersion(
            content_id=content.id,
            version=1,
            title="Synthetic USB-C Hub",
            bullet_points={"values": ["Synthetic feature"]},
            description="Synthetic listing description.",
            marketing_copy="Synthetic marketing copy.",
            source_facts_snapshot={"currency": "SGD", "is_mock_data": True},
            fact_check_result={"passed": True},
            compliance_result={"passed": True},
            change_type="GENERATED",
            change_summary="Initial generated synthetic content.",
            prompt_version_id=prompt_version.id,
            model_invocation_id=invocation.id,
            created_by=admin_user.id,
        )
    )
    report = await report_repository.add(
        GeneratedReport(
            report_type="SELECTION",
            source_entity_type="product_selection_task",
            source_entity_id="synthetic-task-id",
            source_type="simulated_experiment",
            is_mock_data=True,
            format="JSON",
            data_sources={"type": "simulated_experiment"},
            input_conditions={"sites": ["Singapore"]},
            model_invocation_id=invocation.id,
            result_version="selection-v1",
            payload={"is_mock_data": True},
            checksum="c" * 64,
            created_by=admin_user.id,
        )
    )

    assert await prompt_repository.get_template_by_key("listing-localization") == template
    assert await prompt_repository.get_latest_version(template.id) == prompt_version
    prompt_versions, prompt_version_total = await prompt_repository.list_versions(
        template.id,
        1,
        10,
    )
    assert await invocation_repository.get(invocation.id) == invocation
    assert await content_repository.get_version(version.id) == version
    content_versions, content_version_total = await content_repository.list_versions(
        content.id,
        1,
        10,
    )
    assert prompt_version_total == 1
    assert prompt_versions == [prompt_version]
    assert content_version_total == 1
    assert content_versions == [version]
    assert template.status == "ACTIVE"
    assert content.status == "DRAFT"
    assert report.status == "READY"
    reports, report_total = await report_repository.list(
        1,
        10,
        source_entity_type="product_selection_task",
    )
    assert report_total == 1
    assert reports == [report]


@pytest.mark.asyncio
async def test_product_content_scope_is_unique(
    session: AsyncSession,
    admin_user: User,
) -> None:
    repository = ProductContentRepository(session)
    values = {
        "source_product_id": "PROD0001",
        "site": "Singapore",
        "target_language": "English",
        "source_type": "simulated_experiment",
        "source_snapshot_version": "mock-20260727",
        "source_facts": {"currency": "SGD", "is_mock_data": True},
        "is_mock_data": True,
        "created_by": admin_user.id,
    }
    await repository.add_content(ProductContent(**values))

    with pytest.raises(IntegrityError):
        await repository.add_content(ProductContent(**values))


@pytest.mark.asyncio
async def test_generated_report_source_version_is_unique(
    session: AsyncSession,
    admin_user: User,
) -> None:
    repository = GeneratedReportRepository(session)
    values = {
        "report_type": "SELECTION",
        "source_entity_type": "product_selection_task",
        "source_entity_id": "synthetic-task-id",
        "source_type": "simulated_experiment",
        "is_mock_data": True,
        "format": "JSON",
        "data_sources": {"type": "simulated_experiment"},
        "input_conditions": {"sites": ["Singapore"]},
        "result_version": "selection-v1",
        "payload": {"is_mock_data": True},
        "checksum": "f" * 64,
        "created_by": admin_user.id,
    }
    await repository.add(GeneratedReport(**values))

    with pytest.raises(IntegrityError):
        await repository.add(GeneratedReport(**values))
