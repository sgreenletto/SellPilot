import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sellpilot.db.models.commerce import (
    CategoryTrend,
    InventoryRecord,
    LogisticsRecord,
    Order,
    OrderItem,
    Product,
    ReturnRefund,
    Shop,
    Sku,
)
from sellpilot.db.models.tool_call import ToolCall
from sellpilot.schemas.selection import SelectionAnalysisRequest, SelectionCandidateQuery
from sellpilot.services.commerce_import import CommerceImportService
from sellpilot.services.selection import SelectionService
from sellpilot.services.task import TaskService
from sellpilot.tools.runtime import build_tool_registry
from sellpilot.workflows.runner import TaskRunner
from sellpilot.workflows.runtime import build_workflow_registry

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "demo" / "shopee_mock"


@pytest.mark.asyncio
async def test_full_mock_package_completes_all_selection_capabilities(
    session_factory: async_sessionmaker[AsyncSession],
    admin_user,
) -> None:
    active_generations = 0
    maximum_concurrency = 0

    async def explanation_generator(score):
        nonlocal active_generations, maximum_concurrency
        active_generations += 1
        maximum_concurrency = max(maximum_concurrency, active_generations)
        await asyncio.sleep(0.01)
        active_generations -= 1
        return {
            "summary": "经过证据校验的选品解释",
            "evidence": [
                {
                    "metric": "total_score",
                    "value": str(score["total_score"]),
                    "source": "selection formula",
                },
                {
                    "metric": "profit",
                    "value": str(score["profit"]["profit"]),
                    "source": "profit formula",
                },
                {
                    "metric": "margin",
                    "value": str(score["profit"]["margin"]),
                    "source": "margin formula",
                },
                {
                    "metric": "data_completeness",
                    "value": str(score["data_completeness"]),
                    "source": "available dimensions",
                },
            ],
            "risks": list(score["risk_warnings"]),
            "generation_mode": "validated_generator",
        }

    async with session_factory() as session:
        await CommerceImportService(session).import_package(DATA_DIR)
        await session.commit()

        service = SelectionService(session, explanation_generator=explanation_generator)
        analysis = await service.analyze(
            SelectionAnalysisRequest(
                site="sg",
                minimum_profit=Decimal("-1000000"),
                minimum_margin=Decimal("-1"),
                platform_fee_rate=Decimal("0.08"),
                risk_preference="balanced",
            ),
            admin_user.id,
        )

        assert analysis.status == "SUCCEEDED"
        assert analysis.ranked_count > 1
        assert analysis.generation_mode == "validated_generator"
        assert 2 <= maximum_concurrency <= 4
        assert analysis.results == sorted(
            analysis.results,
            key=lambda item: (-item.total_score, -item.data_completeness, item.product_id),
        )
        assert all(
            Decimal("0") < item.data_completeness <= Decimal("1") for item in analysis.results
        )
        incomplete = [item for item in analysis.results if item.data_completeness < Decimal("1")]
        assert incomplete
        assert any(
            "missing review_quality" in warning
            for item in incomplete
            for warning in item.risk_warnings
        )
        for result in analysis.results:
            assert set(result.metrics) == {
                "demand",
                "competition",
                "profitability",
                "review_quality",
                "logistics",
                "after_sales",
                "factory_fit",
            }
            assert any(metric["score"] is not None for metric in result.metrics.values())
            assert result.explanation["summary"]
            assert result.explanation["evidence"]

        compared = await service.compare(
            analysis.task_id,
            [analysis.results[0].product_id, analysis.results[1].product_id],
            admin_user.id,
        )
        assert [item.product_id for item in compared] == [
            analysis.results[0].product_id,
            analysis.results[1].product_id,
        ]

        exported = await service.export(analysis.task_id, admin_user.id)
        assert exported.task.results
        assert exported.filename.endswith(".json")
        assert len(exported.checksum_sha256) == 64


@pytest.mark.asyncio
async def test_selection_service_persists_explainable_mock_results(
    session,
    admin_user,
    test_settings,
) -> None:
    now = datetime.now(UTC)
    shop = Shop(
        external_id="SHOP-SEL",
        name="Mock selection shop",
        platform="shopee",
        mode="mock",
        is_active=True,
        source_type="simulated_experiment",
        is_mock_data=True,
        source_updated_at=now,
    )
    session.add(shop)
    await session.flush()
    products = []
    for index, sales in enumerate((120, 80), start=1):
        product = Product(
            external_id=f"SEL-P{index}",
            shop_id=shop.id,
            source_shop_external_id=shop.external_id,
            title=f"Selection Product {index}",
            category_external_id="CAT-SEL",
            category_name="Selection",
            description="Synthetic test product",
            platform="shopee",
            site="Singapore",
            currency="SGD",
            price=Decimal("50"),
            cost=Decimal("20"),
            shipping_cost=Decimal("5"),
            sales_count=sales,
            rating=Decimal("4.50"),
            review_count=20,
            favorite_count=10,
            status="published",
            source_type="simulated_experiment",
            is_mock_data=True,
            source_created_at=now,
            source_updated_at=now,
            collected_at=now,
        )
        products.append(product)
        session.add(product)
    await session.flush()
    for index, product in enumerate(products, start=1):
        sku = Sku(
            external_id=f"SEL-SKU{index}",
            product_id=product.id,
            seller_sku=f"SEL-SKU-{index}",
            variation_name="Style",
            variation_value="Default",
            price=product.price,
            cost=product.cost,
            weight=Decimal("0.5"),
            status="active",
            source_type="simulated_experiment",
            is_mock_data=True,
            source_created_at=now,
        )
        session.add(sku)
        await session.flush()
        session.add(
            InventoryRecord(
                external_id=f"SEL-INV{index}",
                sku_id=sku.id,
                warehouse_external_id="SEL-WH",
                warehouse_name="Synthetic warehouse",
                available_stock=20,
                reserved_stock=1,
                safety_stock=5,
                stock_status="sufficient",
                source_type="simulated_experiment",
                is_mock_data=True,
                source_updated_at=now,
            )
        )
        order = Order(
            external_id=f"SEL-ORD{index}",
            shop_id=shop.id,
            source_shop_external_id=shop.external_id,
            buyer_external_id=f"SEL-BUY{index}",
            site="Singapore",
            currency="SGD",
            order_status="completed",
            payment_status="paid",
            subtotal=product.price,
            shipping_fee=Decimal("5"),
            discount_amount=Decimal("0"),
            total_amount=product.price + Decimal("5"),
            source_type="simulated_experiment",
            is_mock_data=True,
            source_created_at=now,
            paid_at=now,
            shipped_at=now,
            completed_at=now,
        )
        session.add(order)
        await session.flush()
        order_item = OrderItem(
            external_id=f"SEL-OI{index}",
            order_id=order.id,
            product_id=product.id,
            sku_id=sku.id,
            quantity=1,
            unit_price=product.price,
            subtotal=product.price,
            source_type="simulated_experiment",
            is_mock_data=True,
            source_updated_at=now,
        )
        session.add(order_item)
        session.add(
            LogisticsRecord(
                external_id=f"SEL-LOG{index}",
                order_id=order.id,
                tracking_number=f"SEL-TRACK-{index}",
                carrier="Synthetic carrier",
                status="exception" if index == 1 else "delivered",
                origin="Synthetic origin",
                destination="Singapore",
                estimated_delivery_at=now,
                latest_location="Singapore",
                source_type="simulated_experiment",
                is_mock_data=True,
                source_updated_at=now,
            )
        )
        await session.flush()
        if index == 1:
            session.add(
                ReturnRefund(
                    external_id="SEL-RET1",
                    order_id=order.id,
                    order_item_id=order_item.id,
                    buyer_external_id="SEL-BUY1",
                    request_type="refund_only",
                    reason_type="quality_issue",
                    reason_description="Synthetic selection test return",
                    amount=product.price,
                    status="approved",
                    requested_at=now,
                    source_type="simulated_experiment",
                    is_mock_data=True,
                    source_updated_at=now,
                )
            )
    session.add(
        CategoryTrend(
            external_id="TREND-SEL",
            site="Singapore",
            category_external_id="CAT-SEL",
            category_name="Selection",
            date=date(2026, 7, 27),
            search_index=Decimal("80"),
            sales_index=Decimal("75"),
            competition_index=Decimal("30"),
            average_price=Decimal("50"),
            growth_rate=Decimal("0.10"),
            source_type="simulated_experiment",
            is_mock_data=True,
            source_updated_at=now,
        )
    )
    await session.flush()

    result = await SelectionService(session).analyze(
        SelectionAnalysisRequest(
            site="sg",
            category_id="CAT-SEL",
            platform_fee_rate=Decimal("0.10"),
            cost_override=Decimal("10"),
            shipping_cost_override=Decimal("2"),
            product_weight_kg=Decimal("0.5"),
            risk_preference="conservative",
        ),
        admin_user.id,
    )

    assert result.status == "SUCCEEDED"
    assert result.ranked_count == 2
    assert result.generation_mode == "rule_template"
    assert result.formula_version == "selection-v1.0.0-conservative"
    assert result.results[0].profit["profit"] == "33.00"
    assert result.results[0].is_mock_data is True
    assert result.results[0].explanation["generation_mode"] == "rule_template"
    assert result.results[0].data_completeness == Decimal("1.0000")
    assert all(metric["score"] is not None for metric in result.results[0].metrics.values())

    fetched = await SelectionService(session).get_task(result.task_id, admin_user.id)
    assert len(fetched.results) == 2
    assert fetched.criteria["product_weight_kg"] == "0.5"
    exported = await SelectionService(session).export(result.task_id, admin_user.id)
    assert exported.filename.endswith(".json")
    assert len(exported.checksum_sha256) == 64

    workflow_registry = build_workflow_registry(test_settings)
    workflow_request = SelectionAnalysisRequest(
        site="sg",
        category_id="CAT-SEL",
        platform_fee_rate=Decimal("0.10"),
    )
    workflow_task = await TaskService(session, test_settings).create_workflow_task(
        workflow_registry.get("selection"),
        workflow_input=workflow_request.model_dump(mode="json"),
        created_by=admin_user.id,
        request_id=str(uuid4()),
    )
    workflow_result = await TaskRunner(
        workflow_registry,
        build_tool_registry(test_settings),
        session,
        test_settings,
    ).run(workflow_task.id, user_id=admin_user.id)
    assert workflow_result.status == "succeeded"
    assert workflow_result.result["analysis"]["ranked_count"] == result.ranked_count
    workflow_call = await session.scalar(
        select(ToolCall).where(ToolCall.task_id == workflow_task.id)
    )
    assert workflow_call is not None
    assert workflow_call.task_step_id is not None

    second_page = await SelectionService(session).list_candidates(
        SelectionCandidateQuery(site="sg", category_id="CAT-SEL", offset=1, limit=1)
    )
    assert len(second_page) == 1
    assert second_page[0].product_id == "SEL-P2"
