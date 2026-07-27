from decimal import Decimal

import pytest
from pydantic import ValidationError

from sellpilot.domain.selection import (
    DEFAULT_SELECTION_CONFIG,
    SelectionCandidate,
    SelectionCriteria,
    SelectionFormulaConfig,
    calculate_profit,
    score_candidates,
)
from sellpilot.domain.selection.models import SelectionMetric


def candidate(product_id: str, **overrides) -> SelectionCandidate:
    values = {
        "product_id": product_id,
        "site": "Singapore",
        "currency": "SGD",
        "source_type": "simulated_experiment",
        "is_mock_data": True,
        "price": Decimal("100.00"),
        "cost": Decimal("50.00"),
        "shipping_cost": Decimal("10.00"),
        "platform_fee_rate": Decimal("0.05"),
        "other_costs": Decimal("2.00"),
        "sales_count": 100,
        "search_index": Decimal("50"),
        "sales_index": Decimal("45"),
        "growth_rate": Decimal("0.10"),
        "competition_index": Decimal("40"),
        "rating": Decimal("4.5"),
        "review_count": 50,
        "logistics_risk_rate": Decimal("0.10"),
        "after_sales_rate": Decimal("0.05"),
        "factory_fit_score": Decimal("0.80"),
    }
    values.update(overrides)
    return SelectionCandidate(**values)


@pytest.mark.parametrize(
    ("price", "cost", "shipping", "expected_profit", "expected_margin"),
    [
        ("100", "50", "10", "40.00", "0.4000"),
        ("100", "90", "10", "0.00", "0.0000"),
        ("100", "95", "10", "-5.00", "-0.0500"),
    ],
)
def test_calculate_profit_handles_positive_zero_and_negative(
    price,
    cost,
    shipping,
    expected_profit,
    expected_margin,
):
    item = candidate(
        "profit-case",
        price=Decimal(price),
        cost=Decimal(cost),
        shipping_cost=Decimal(shipping),
        platform_fee_rate=Decimal("0"),
        other_costs=Decimal("0"),
    )

    result = calculate_profit(item)

    assert result.profit == Decimal(expected_profit)
    assert result.margin == Decimal(expected_margin)


def test_profit_rounding_is_decimal_and_half_up():
    item = candidate(
        "rounding",
        price=Decimal("10.05"),
        cost=Decimal("1"),
        shipping_cost=Decimal("0"),
        platform_fee_rate=Decimal("0.015"),
        other_costs=Decimal("0"),
    )

    result = calculate_profit(item)

    assert result.platform_fee == Decimal("0.15")
    assert result.profit == Decimal("8.90")


def test_minimum_profit_and_margin_boundaries_are_inclusive():
    item = candidate(
        "boundary",
        platform_fee_rate=Decimal("0"),
        other_costs=Decimal("0"),
    )

    included = score_candidates(
        [item],
        SelectionCriteria(
            minimum_profit=Decimal("40.00"),
            minimum_margin=Decimal("0.4000"),
        ),
    )
    excluded = score_candidates(
        [item],
        SelectionCriteria(minimum_profit=Decimal("40.01")),
    )

    assert [score.product_id for score in included.ranked] == ["boundary"]
    assert not included.excluded
    assert not excluded.ranked
    assert excluded.excluded[0].reasons == ("profit 40.00 is below minimum 40.01",)


def test_single_candidate_and_equal_values_use_neutral_cohort_scores():
    single = score_candidates([candidate("only")]).ranked[0]
    equal = score_candidates([candidate("b"), candidate("a")]).ranked

    assert single.metrics[SelectionMetric.DEMAND].score == Decimal("50.0000")
    assert single.metrics[SelectionMetric.COMPETITION].score == Decimal("50")
    assert single.metrics[SelectionMetric.PROFITABILITY].score == Decimal("50")
    assert [result.product_id for result in equal] == ["a", "b"]
    assert [result.rank for result in equal] == [1, 2]


def test_extreme_outlier_has_defined_bounded_result():
    result = score_candidates(
        [
            candidate("normal-a", sales_count=10),
            candidate("normal-b", sales_count=20),
            candidate("outlier", sales_count=10**12),
        ]
    )

    assert all(Decimal("0") <= item.total_score <= Decimal("100") for item in result.ranked)
    outlier = next(item for item in result.ranked if item.product_id == "outlier")
    assert outlier.metrics[SelectionMetric.DEMAND].score <= Decimal("100")


def test_config_rejects_bad_weight_sum_negative_and_unknown_metric():
    valid_weights = dict(DEFAULT_SELECTION_CONFIG.weights)
    bad_sum = {**valid_weights, SelectionMetric.DEMAND: Decimal("0.24")}
    negative = {
        **valid_weights,
        SelectionMetric.DEMAND: Decimal("-0.01"),
        SelectionMetric.PROFITABILITY: Decimal("0.51"),
    }
    unknown = {metric.value: weight for metric, weight in valid_weights.items()}
    unknown["unknown"] = unknown.pop("factory_fit")

    with pytest.raises(ValidationError, match="sum exactly to 1"):
        SelectionFormulaConfig(version="bad-sum", weights=bad_sum)
    with pytest.raises(ValidationError, match="must not be negative"):
        SelectionFormulaConfig(version="negative", weights=negative)
    with pytest.raises(ValidationError):
        SelectionFormulaConfig(version="unknown", weights=unknown)


def test_missing_optional_sources_are_explicit_and_reduce_confidence():
    complete, incomplete = score_candidates(
        [
            candidate("complete"),
            candidate(
                "incomplete",
                search_index=None,
                sales_index=None,
                growth_rate=None,
                rating=None,
                review_count=None,
                after_sales_rate=None,
                logistics_risk_rate=None,
                factory_fit_score=None,
            ),
        ]
    ).ranked

    assert incomplete.metrics[SelectionMetric.REVIEW_QUALITY].score is None
    assert incomplete.metrics[SelectionMetric.REVIEW_QUALITY].missing_reason
    assert incomplete.metrics[SelectionMetric.AFTER_SALES].score is None
    assert incomplete.data_completeness < complete.data_completeness
    assert incomplete.confidence < complete.confidence
    assert any("missing review_quality" in warning for warning in incomplete.risk_warnings)


def test_zero_rating_and_zero_reviews_match_mock_data_no_review_marker():
    result = score_candidates(
        [candidate("no-reviews", rating=Decimal("0.00"), review_count=0)]
    ).ranked[0]

    assert result.metrics[SelectionMetric.REVIEW_QUALITY].score is None
    assert result.metrics[SelectionMetric.REVIEW_QUALITY].inputs == {
        "rating": Decimal("0.00"),
        "review_count": 0,
    }
    with pytest.raises(ValidationError, match="rating must be 0"):
        candidate("bad-empty-rating", rating=Decimal("4"), review_count=0)
    with pytest.raises(ValidationError, match="between 1 and 5"):
        candidate("bad-rated-product", rating=Decimal("0"), review_count=1)


def test_currency_and_site_cohorts_are_normalized_independently():
    baseline = score_candidates(
        [
            candidate("sg-low", sales_count=10),
            candidate("sg-high", sales_count=20),
            candidate("my-low", site="Malaysia", currency="MYR", sales_count=100),
            candidate("my-high", site="Malaysia", currency="MYR", sales_count=200),
        ]
    )
    changed = score_candidates(
        [
            candidate("sg-low", sales_count=10),
            candidate("sg-high", sales_count=10**12),
            candidate("my-low", site="Malaysia", currency="MYR", sales_count=100),
            candidate("my-high", site="Malaysia", currency="MYR", sales_count=200),
        ]
    )

    baseline_my = {
        item.product_id: item.total_score for item in baseline.ranked if item.currency == "MYR"
    }
    changed_my = {
        item.product_id: item.total_score for item in changed.ranked if item.currency == "MYR"
    }
    assert baseline_my == changed_my
    assert baseline.cohort_keys == ("Malaysia:MYR", "Singapore:SGD")


def test_ranking_is_stable_for_reordered_input_and_has_unique_global_ranks():
    items = [
        candidate("c", sales_count=30),
        candidate("a", sales_count=10),
        candidate("b", sales_count=20),
    ]

    first = score_candidates(items)
    second = score_candidates(reversed(items))

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [item.rank for item in first.ranked] == [1, 2, 3]


def test_duplicate_product_id_is_rejected():
    with pytest.raises(ValueError, match="product_id must be unique"):
        score_candidates([candidate("duplicate"), candidate("duplicate")])


def test_empty_batch_has_a_defined_result():
    result = score_candidates([])

    assert result.ranked == ()
    assert result.excluded == ()
    assert result.cohort_keys == ()


def test_fixed_golden_dataset_result():
    result = score_candidates(
        [
            candidate(
                "alpha",
                price=Decimal("80"),
                cost=Decimal("40"),
                shipping_cost=Decimal("8"),
                platform_fee_rate=Decimal("0"),
                other_costs=Decimal("0"),
                sales_count=80,
                search_index=Decimal("70"),
                sales_index=Decimal("65"),
                growth_rate=Decimal("0.20"),
                competition_index=Decimal("30"),
                rating=Decimal("4.6"),
                review_count=80,
                logistics_risk_rate=Decimal("0.08"),
                after_sales_rate=Decimal("0.04"),
                factory_fit_score=Decimal("0.90"),
            ),
            candidate(
                "beta",
                price=Decimal("75"),
                cost=Decimal("45"),
                shipping_cost=Decimal("10"),
                platform_fee_rate=Decimal("0"),
                other_costs=Decimal("0"),
                sales_count=40,
                search_index=Decimal("45"),
                sales_index=Decimal("42"),
                growth_rate=Decimal("-0.05"),
                competition_index=Decimal("60"),
                rating=Decimal("4.0"),
                review_count=30,
                logistics_risk_rate=Decimal("0.20"),
                after_sales_rate=Decimal("0.12"),
                factory_fit_score=Decimal("0.60"),
            ),
        ]
    )

    assert [(item.product_id, item.total_score) for item in result.ranked] == [
        ("alpha", Decimal("97.3800")),
        ("beta", Decimal("24.8400")),
    ]
    assert result.ranked[0].formula_version == "selection-v1.0.0"
