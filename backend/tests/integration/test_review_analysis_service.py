from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from sellpilot.core.enums import (
    AnalysisStatus,
    TaskStatus,
    TaskStepStatus,
    ToolCallerType,
    ToolCallStatus,
)
from sellpilot.core.exceptions import IdempotencyConflictError
from sellpilot.db.models.agent_task import AgentTask
from sellpilot.db.models.commerce import Product, Review, Shop
from sellpilot.domain.review_analysis import analyze_reviews
from sellpilot.repositories.task import TaskRepository
from sellpilot.schemas.review_analysis import (
    ReviewAnalysisCreateRequest,
    ReviewQuery,
)
from sellpilot.services.review_analysis import ReviewAnalysisService
from sellpilot.services.task import TaskService
from sellpilot.tools.contracts import ToolExecutionContext
from sellpilot.tools.executor import ToolExecutor
from sellpilot.tools.runtime import build_tool_registry
from sellpilot.workflows.runner import TaskRunner
from sellpilot.workflows.runtime import build_workflow_registry


async def seed_reviews(session, *, review_count: int = 4) -> Product:
    now = datetime.now(UTC)
    shop = Shop(
        external_id="SHOP-REV",
        name="Mock review shop",
        platform="shopee",
        mode="mock",
        is_active=True,
        source_type="simulated_experiment",
        is_mock_data=True,
        source_updated_at=now,
    )
    session.add(shop)
    await session.flush()
    product = Product(
        external_id="REV-P1",
        shop_id=shop.id,
        source_shop_external_id=shop.external_id,
        title="Review Product",
        category_external_id="CAT-REV",
        category_name="Review",
        description="Synthetic review product",
        platform="shopee",
        site="Singapore",
        currency="SGD",
        price=Decimal("50"),
        cost=Decimal("20"),
        shipping_cost=Decimal("5"),
        sales_count=100,
        rating=Decimal("4.00"),
        review_count=review_count,
        favorite_count=10,
        status="active",
        source_type="simulated_experiment",
        is_mock_data=True,
        source_created_at=now,
        source_updated_at=now,
        collected_at=now,
    )
    session.add(product)
    await session.flush()
    samples = [
        (1, "Broken product and damaged packaging", "English", "product"),
        (3, "The item is acceptable", "English", "none"),
        (5, "Produk bagus dan pengiriman cepat", "Indonesian", "none"),
        (2, "Maayos ang item pero huli ang delivery", "Filipino", "logistics"),
    ]
    for index in range(review_count):
        rating, content, language, issue = samples[index % len(samples)]
        session.add(
            Review(
                external_id=f"REV-SVC-{index + 1}",
                product_id=product.id,
                buyer_external_id=f"BUY-{index + 1}",
                rating=rating,
                content=f"{content} {index + 1}",
                content_zh=f"模拟译文 {index + 1}",
                language=language,
                sentiment_hint="negative" if rating <= 2 else "positive",
                issue_type=issue,
                source_created_at=now - timedelta(days=index),
                source_type="simulated_experiment",
                is_mock_data=True,
                source_updated_at=now,
            )
        )
    await session.flush()
    return product


async def test_review_service_creates_runs_persists_steps_and_evidence(
    session,
    admin_user,
    test_settings,
):
    await seed_reviews(session)
    service = ReviewAnalysisService(session, test_settings)
    request = ReviewAnalysisCreateRequest(
        idempotency_key="review-service-001",
        product_id="REV-P1",
        site="sg",
        batch_size=2,
        maximum_reviews=4,
    )

    created = await service.create(request, admin_user.id)
    assert created.status is AnalysisStatus.PENDING
    assert created.duplicate is False
    pending = await service.get(created.analysis_id, admin_user.id)
    assert pending.quality is None
    assert pending.analysis_mode == "rule"
    assert pending.progress == 0
    assert len(pending.steps) == 3
    assert all(step.status is TaskStepStatus.PENDING for step in pending.steps)
    assert pending.prompt_version is None
    assert pending.model_version is None

    result = await service.run(created.analysis_id, admin_user.id)
    assert result.status is AnalysisStatus.SUCCEEDED
    assert result.quality.included_count == 4
    assert result.topics
    assert result.pain_points
    assert result.keywords
    assert result.judgements
    assert result.analyzer_version == "review-analysis-v1.1.0"
    assert result.analysis_mode == "rule"
    assert result.progress == 100
    assert result.current_step == "persist_results"
    assert all(step.status is TaskStepStatus.SUCCEEDED for step in result.steps)

    evidence = await service.list_evidence(
        created.analysis_id,
        admin_user.id,
        page=1,
        page_size=2,
    )
    assert evidence.total >= 4
    assert len(evidence.items) == 2
    assert all(item.review_id.startswith("REV-SVC-") for item in evidence.items)

    task = await service.tasks.get(created.agent_task_id)
    assert TaskStatus(task.status) is TaskStatus.SUCCEEDED
    assert task.current_step == "persist_results"
    steps = await TaskRepository(session).list_steps(task.id)
    assert {step.step_name for step in steps} == {
        "load_reviews",
        "analyze_reviews",
        "persist_results",
    }
    assert all(TaskStepStatus(step.status) is TaskStepStatus.SUCCEEDED for step in steps)


async def test_review_service_idempotency_reuses_exact_request_and_rejects_conflict(
    session,
    admin_user,
    test_settings,
):
    await seed_reviews(session)
    service = ReviewAnalysisService(session, test_settings)
    request = ReviewAnalysisCreateRequest(
        idempotency_key="review-idempotent-001",
        product_id="REV-P1",
    )
    first = await service.create(request, admin_user.id)
    duplicate = await service.create(request, admin_user.id)

    assert duplicate.analysis_id == first.analysis_id
    assert duplicate.duplicate is True
    with pytest.raises(IdempotencyConflictError):
        await service.create(
            request.model_copy(update={"maximum_reviews": 2}),
            admin_user.id,
        )


async def test_review_service_filters_and_batches_reviews(
    session,
    admin_user,
    test_settings,
):
    await seed_reviews(session, review_count=7)
    service = ReviewAnalysisService(session, test_settings)

    page = await service.list_reviews(
        ReviewQuery(
            product_id="REV-P1",
            site="sg",
            min_rating=1,
            max_rating=2,
            offset=0,
            limit=2,
        )
    )
    assert len(page) == 2
    assert all(item.rating <= 2 for item in page)

    created = await service.create(
        ReviewAnalysisCreateRequest(
            idempotency_key="review-batches-001",
            product_id="REV-P1",
            batch_size=2,
            maximum_reviews=5,
        ),
        admin_user.id,
    )
    result = await service.run(created.analysis_id, admin_user.id)
    assert result.quality.received_count == 5


async def test_review_service_retries_analyzer_and_records_retry_count(
    session,
    admin_user,
    test_settings,
):
    await seed_reviews(session)
    attempts = 0

    async def flaky_analyzer(reviews):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("synthetic first attempt")
        return await analyze_reviews(reviews)

    service = ReviewAnalysisService(session, test_settings, analyzer=flaky_analyzer)
    created = await service.create(
        ReviewAnalysisCreateRequest(
            idempotency_key="review-retry-001",
            product_id="REV-P1",
            max_attempts=2,
        ),
        admin_user.id,
    )
    result = await service.run(created.analysis_id, admin_user.id)

    assert result.status is AnalysisStatus.SUCCEEDED
    assert attempts == 2
    task = await service.tasks.get(created.agent_task_id)
    assert task.retry_count == 1


async def test_review_service_returns_audited_no_data_result_without_server_error(
    session,
    admin_user,
    test_settings,
):
    await seed_reviews(session, review_count=0)
    service = ReviewAnalysisService(session, test_settings)
    created = await service.create(
        ReviewAnalysisCreateRequest(
            idempotency_key="review-empty-001",
            product_id="REV-P1",
        ),
        admin_user.id,
    )

    result = await service.run(created.analysis_id, admin_user.id)

    assert result.status is AnalysisStatus.SUCCEEDED
    assert result.no_data is True
    assert result.quality.received_count == 0
    assert result.sentiment.positive == 0
    assert result.topics == ()
    assert result.pain_points == ()
    assert result.data_source == "simulated_experiment"
    task = await service.tasks.get(created.agent_task_id)
    assert TaskStatus(task.status) is TaskStatus.SUCCEEDED
    assert task.result["no_data"] is True
    assert all(step.status is TaskStepStatus.SUCCEEDED for step in result.steps)


async def test_review_service_resolves_display_product_alias_to_stable_external_id(
    session,
    admin_user,
    test_settings,
):
    product = await seed_reviews(session, review_count=2)
    product.external_id = "PROD0001"
    await session.flush()
    service = ReviewAnalysisService(session, test_settings)

    created = await service.create(
        ReviewAnalysisCreateRequest(
            idempotency_key="review-product-alias-001",
            product_id="PROD-001",
        ),
        admin_user.id,
    )
    result = await service.run(created.analysis_id, admin_user.id)

    assert result.status is AnalysisStatus.SUCCEEDED
    assert result.product_id == "PROD0001"
    assert result.quality.received_count == 2


async def test_review_tools_use_unified_executor_and_persist_traceable_analysis(
    session,
    admin_user,
    test_settings,
):
    await seed_reviews(session)
    registry = build_tool_registry(test_settings)
    executor = ToolExecutor(registry, session, test_settings)
    context = ToolExecutionContext(
        request_id=str(uuid4()),
        user_id=admin_user.id,
        caller_type=ToolCallerType.TEST,
        caller_name="review_analysis_test",
    )

    reviews = await executor.execute(
        "get_product_reviews",
        {"product_id": "REV-P1", "site": "sg", "limit": 2},
        context,
    )
    assert reviews.status is ToolCallStatus.SUCCEEDED
    assert reviews.data["count"] == 2
    assert reviews.duration_ms >= 0

    analysis = await executor.execute(
        "analyze_product_reviews",
        {
            "idempotency_key": "review-tool-analysis-001",
            "product_id": "REV-P1",
            "site": "sg",
            "batch_size": 2,
            "maximum_reviews": 4,
            "max_attempts": 2,
        },
        context.model_copy(update={"request_id": str(uuid4())}),
    )
    assert analysis.status is ToolCallStatus.SUCCEEDED
    assert analysis.data["analysis"]["status"] == "SUCCEEDED"
    assert analysis.data["analysis"]["analysis_mode"] == "rule"
    assert analysis.attempt_count == 1


async def test_review_analysis_uses_task_workflow_runtime_without_nested_task(
    session,
    admin_user,
    test_settings,
):
    await seed_reviews(session)
    workflows = build_workflow_registry(test_settings)
    tools = build_tool_registry(test_settings)
    definition = workflows.get("review_analysis")
    task = await TaskService(session, test_settings).create_workflow_task(
        definition,
        workflow_input={
            "idempotency_key": "review-workflow-analysis-001",
            "product_id": "REV-P1",
            "site": "sg",
            "batch_size": 2,
            "maximum_reviews": 4,
            "max_attempts": 2,
        },
        created_by=admin_user.id,
        request_id=str(uuid4()),
    )

    result = await TaskRunner(
        workflows,
        tools,
        session,
        test_settings,
    ).run(task.id, user_id=admin_user.id)

    assert result.status is TaskStatus.SUCCEEDED
    assert result.result["analysis"]["status"] == "SUCCEEDED"
    assert await session.scalar(select(func.count()).select_from(AgentTask)) == 1
    steps = await TaskRepository(session).list_steps(task.id)
    assert [step.step_name for step in steps] == [
        "analyze_product_reviews",
        "load_reviews",
        "analyze_reviews",
        "persist_results",
    ]
    assert all(TaskStepStatus(step.status) is TaskStepStatus.SUCCEEDED for step in steps)
    assert steps[0].tool_call_id is not None


async def test_product_improvement_report_uses_task_workflow_runtime(
    session,
    admin_user,
    test_settings,
):
    await seed_reviews(session)
    review_service = ReviewAnalysisService(session, test_settings)
    review = await review_service.create(
        ReviewAnalysisCreateRequest(
            idempotency_key="review-for-improvement-workflow-001",
            product_id="REV-P1",
            maximum_reviews=4,
        ),
        admin_user.id,
    )
    await review_service.run(review.analysis_id, admin_user.id)

    workflows = build_workflow_registry(test_settings)
    task = await TaskService(session, test_settings).create_workflow_task(
        workflows.get("product_improvement"),
        workflow_input={"analysis_id": str(review.analysis_id)},
        created_by=admin_user.id,
        request_id=str(uuid4()),
    )
    result = await TaskRunner(
        workflows,
        build_tool_registry(test_settings),
        session,
        test_settings,
    ).run(task.id, user_id=admin_user.id)

    assert result.status is TaskStatus.SUCCEEDED
    assert result.result["report"]["algorithm_version"] == "product-improvement-rule-v1.2.0"
    steps = await TaskRepository(session).list_steps(task.id)
    assert [step.step_name for step in steps] == [
        "select_improvement_source",
        "generate_product_improvement_plan",
    ]
    assert steps[0].output_summary["selected_branch"] == "generate_product_improvement_plan"
    assert all(TaskStepStatus(step.status) is TaskStepStatus.SUCCEEDED for step in steps)
    assert steps[0].tool_call_id is None
    assert steps[1].tool_call_id is not None
