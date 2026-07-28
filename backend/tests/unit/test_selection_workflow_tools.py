from decimal import Decimal

import pytest

from sellpilot.core.enums import CurrencyCode, DataSource, SiteCode, ToolRiskLevel
from sellpilot.domain.selection.models import SelectionCandidate
from sellpilot.schemas.common import SourceMetadata
from sellpilot.tools.contracts import ToolContext
from sellpilot.tools.selection import build_selection_tool_registry
from sellpilot.workflows.selection import generate_validated_explanation


def _score_payload() -> dict[str, object]:
    return {
        "total_score": "82.1000",
        "formula_version": "selection-v1.0.0",
        "data_completeness": "0.7500",
        "profit": {"profit": "12.00", "margin": "0.2400"},
        "recommendation_facts": ["综合评分 82.1000", "单件利润 12.00"],
        "risk_warnings": ["factory_fit data missing"],
    }


@pytest.mark.asyncio
async def test_explanation_rejects_mismatched_generated_metrics_and_falls_back() -> None:
    attempts = 0

    async def invalid_generator(_payload):
        nonlocal attempts
        attempts += 1
        return {
            "summary": "unsupported claim",
            "evidence": [
                {"metric": "total_score", "value": "99", "source": "invented"},
                {"metric": "profit", "value": "12.00", "source": "calculation"},
                {"metric": "margin", "value": "0.2400", "source": "calculation"},
                {
                    "metric": "data_completeness",
                    "value": "0.7500",
                    "source": "calculation",
                },
            ],
            "risks": [],
            "generation_mode": "validated_generator",
        }

    result = await generate_validated_explanation(
        _score_payload(), invalid_generator, max_attempts=2
    )

    assert attempts == 2
    assert result.generation_mode == "rule_template"
    assert {item.metric for item in result.evidence} == {
        "total_score",
        "profit",
        "margin",
        "data_completeness",
    }


@pytest.mark.asyncio
async def test_profit_tool_is_schema_validated_and_read_only() -> None:
    registry = build_selection_tool_registry()
    definition = registry.get("calculate_product_profit")
    assert definition.risk_level is ToolRiskLevel.READ
    assert definition.requires_confirmation is False
    assert len(registry.list()) == 5

    candidate = SelectionCandidate(
        product_id="P001",
        site=SiteCode.SG,
        currency=CurrencyCode.SGD,
        source=SourceMetadata(
            source_type=DataSource.MOCK,
            source_name="simulated_experiment",
            source_reference="P001",
            is_mock=True,
        ),
        price=Decimal("50"),
        cost=Decimal("20"),
        shipping_cost=Decimal("5"),
        platform_fee_rate=Decimal("0.10"),
    )
    result = await registry.invoke(
        "calculate_product_profit",
        {"candidate": candidate.model_dump(mode="json")},
        ToolContext(),
    )

    assert result.success is True
    assert result.data["profit"]["profit"] == "20.00"
