from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from sellpilot.db.models.commerce import CategoryTrend, Product, Shop
from sellpilot.schemas.selection import SelectionAnalysisRequest, SelectionCandidateQuery
from sellpilot.services.selection import SelectionService


@pytest.mark.asyncio
async def test_selection_service_persists_explainable_mock_results(session, admin_user) -> None:
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
    for index, sales in enumerate((120, 80), start=1):
        session.add(
            Product(
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
        ),
        admin_user.id,
    )

    assert result.status == "SUCCEEDED"
    assert result.ranked_count == 2
    assert result.generation_mode == "rule_template"
    assert result.results[0].profit["profit"] == "20.00"
    assert result.results[0].is_mock_data is True
    assert result.results[0].explanation["generation_mode"] == "rule_template"

    fetched = await SelectionService(session).get_task(result.task_id, admin_user.id)
    assert len(fetched.results) == 2
    exported = await SelectionService(session).export(result.task_id, admin_user.id)
    assert exported.filename.endswith(".json")
    assert len(exported.checksum_sha256) == 64

    second_page = await SelectionService(session).list_candidates(
        SelectionCandidateQuery(site="sg", category_id="CAT-SEL", offset=1, limit=1)
    )
    assert len(second_page) == 1
    assert second_page[0].product_id == "SEL-P2"
