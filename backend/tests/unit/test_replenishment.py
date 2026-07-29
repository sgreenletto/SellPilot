from decimal import Decimal

from sellpilot.core.config import Settings
from sellpilot.repositories.replenishment import ReplenishmentSourceRow
from sellpilot.schemas.replenishment import ReplenishmentAnalysisRequest
from sellpilot.services.replenishment import ReplenishmentService
from sellpilot.tools.runtime import build_tool_registry
from sellpilot.workflows.runtime import build_workflow_registry


def test_replenishment_calculation_uses_recent_demand_and_safety_stock() -> None:
    request = ReplenishmentAnalysisRequest(
        shop_external_id="SHOP001",
        analysis_days=30,
        lead_time_days=14,
        safety_factor=Decimal("1.20"),
        only_replenishment=True,
    )
    result = ReplenishmentService.calculate_recommendation(
        ReplenishmentSourceRow(
            product_id="PROD001",
            product_title="Synthetic Product",
            sku_id="SKU001",
            seller_sku="SELLER-SKU-001",
            site="Singapore",
            available_stock=10,
            safety_stock=5,
            units_sold=60,
            is_mock_data=True,
        ),
        request,
    )

    assert result.average_daily_sales == Decimal("2.0000")
    assert result.days_of_supply == Decimal("5.0000")
    assert result.target_stock == 34
    assert result.recommended_quantity == 24
    assert result.risk_level == "critical"
    assert result.is_mock_data is True


def test_replenishment_calculation_keeps_zero_demand_sku_healthy() -> None:
    request = ReplenishmentAnalysisRequest(shop_external_id="SHOP001")
    result = ReplenishmentService.calculate_recommendation(
        ReplenishmentSourceRow(
            product_id="PROD002",
            product_title="Synthetic Product 2",
            sku_id="SKU002",
            seller_sku="SELLER-SKU-002",
            site="Singapore",
            available_stock=20,
            safety_stock=5,
            units_sold=0,
            is_mock_data=True,
        ),
        request,
    )

    assert result.days_of_supply is None
    assert result.target_stock == 0
    assert result.recommended_quantity == 0
    assert result.risk_level == "healthy"


def test_replenishment_does_not_refill_a_conservative_static_threshold() -> None:
    request = ReplenishmentAnalysisRequest(
        shop_external_id="SHOP001",
        analysis_days=90,
        lead_time_days=14,
        safety_factor=Decimal("1.20"),
    )
    result = ReplenishmentService.calculate_recommendation(
        ReplenishmentSourceRow(
            product_id="PROD003",
            product_title="Slow-moving Synthetic Product",
            sku_id="SKU003",
            seller_sku="SELLER-SKU-003",
            site="Singapore",
            available_stock=5,
            safety_stock=15,
            units_sold=2,
            is_mock_data=True,
        ),
        request,
    )

    assert result.target_stock == 1
    assert result.recommended_quantity == 0
    assert result.risk_level == "healthy"
    assert "建议复核阈值" in result.reason


def test_replenishment_tool_and_workflow_are_registered() -> None:
    test_settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test",
        JWT_SECRET_KEY="test-only-jwt-secret-with-at-least-32-characters",
        PLATFORM_ADAPTER="mock",
    )
    tool = build_tool_registry(test_settings).get("analyze_inventory_replenishment")
    workflow = build_workflow_registry(test_settings).get("inventory_replenishment")

    assert tool.risk_level.value == "read"
    assert tool.confirmation_required is False
    assert workflow.task_type.value == "replenishment"
    assert workflow.output_schema.__name__ == "ReplenishmentAnalysisOutput"
