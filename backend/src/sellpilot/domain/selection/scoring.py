from collections.abc import Iterable, Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal

from sellpilot.domain.selection.models import (
    CandidateExclusion,
    CandidateScore,
    MetricEvidence,
    ProfitBreakdown,
    SelectionBatchResult,
    SelectionCandidate,
    SelectionCriteria,
    SelectionFormulaConfig,
    SelectionMetric,
)

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")

DEFAULT_SELECTION_CONFIG = SelectionFormulaConfig(
    version="selection-v1.0.0",
    weights={
        SelectionMetric.DEMAND: Decimal("0.25"),
        SelectionMetric.COMPETITION: Decimal("0.15"),
        SelectionMetric.PROFITABILITY: Decimal("0.25"),
        SelectionMetric.REVIEW_QUALITY: Decimal("0.12"),
        SelectionMetric.LOGISTICS: Decimal("0.08"),
        SelectionMetric.AFTER_SALES: Decimal("0.08"),
        SelectionMetric.FACTORY_FIT: Decimal("0.07"),
    },
)


def _quantize(value: Decimal, quantum: Decimal) -> Decimal:
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def _clamp(value: Decimal, lower: Decimal = ZERO, upper: Decimal = HUNDRED) -> Decimal:
    return min(max(value, lower), upper)


def calculate_profit(
    candidate: SelectionCandidate,
    config: SelectionFormulaConfig = DEFAULT_SELECTION_CONFIG,
) -> ProfitBreakdown:
    platform_fee = _quantize(
        candidate.price * candidate.platform_fee_rate,
        config.money_quantum,
    )
    total_cost = _quantize(
        candidate.cost + candidate.shipping_cost + platform_fee + candidate.other_costs,
        config.money_quantum,
    )
    profit = _quantize(candidate.price - total_cost, config.money_quantum)
    margin = _quantize(profit / candidate.price, config.score_quantum)
    return ProfitBreakdown(
        price=_quantize(candidate.price, config.money_quantum),
        cost=_quantize(candidate.cost, config.money_quantum),
        shipping_cost=_quantize(candidate.shipping_cost, config.money_quantum),
        platform_fee=platform_fee,
        other_costs=_quantize(candidate.other_costs, config.money_quantum),
        total_cost=total_cost,
        profit=profit,
        margin=margin,
    )


def _cohort_key(candidate: SelectionCandidate) -> tuple[str, str]:
    return candidate.site, candidate.currency


def _normalize(
    value: Decimal,
    available_values: Sequence[Decimal],
    config: SelectionFormulaConfig,
    *,
    reverse: bool = False,
) -> Decimal:
    minimum = min(available_values)
    maximum = max(available_values)
    if minimum == maximum:
        return config.neutral_score
    score = (value - minimum) / (maximum - minimum) * HUNDRED
    if reverse:
        score = HUNDRED - score
    return _quantize(_clamp(score), config.score_quantum)


def _fixed_rate_score(
    value: Decimal,
    config: SelectionFormulaConfig,
    *,
    reverse: bool = False,
) -> Decimal:
    score = _clamp(value, ZERO, ONE) * HUNDRED
    if reverse:
        score = HUNDRED - score
    return _quantize(score, config.score_quantum)


def _growth_value(value: Decimal, config: SelectionFormulaConfig) -> Decimal:
    return _clamp(value, config.growth_floor, config.growth_ceiling)


def _component_average(values: Sequence[Decimal], config: SelectionFormulaConfig) -> Decimal:
    return _quantize(sum(values, ZERO) / Decimal(len(values)), config.score_quantum)


def _cohort_values(
    cohort: Sequence[SelectionCandidate],
    field: str,
    config: SelectionFormulaConfig,
) -> list[Decimal]:
    values: list[Decimal] = []
    for candidate in cohort:
        value = getattr(candidate, field)
        if value is None:
            continue
        decimal_value = Decimal(value)
        if field == "growth_rate":
            decimal_value = _growth_value(decimal_value, config)
        values.append(decimal_value)
    return values


def _demand_score(
    candidate: SelectionCandidate,
    cohort: Sequence[SelectionCandidate],
    config: SelectionFormulaConfig,
) -> tuple[Decimal | None, dict[str, Decimal | int | None]]:
    inputs: dict[str, Decimal | int | None] = {
        "sales_count": candidate.sales_count,
        "search_index": candidate.search_index,
        "sales_index": candidate.sales_index,
        "growth_rate": candidate.growth_rate,
    }
    component_scores: list[Decimal] = []
    for field in inputs:
        value = getattr(candidate, field)
        if value is None:
            continue
        decimal_value = Decimal(value)
        if field == "growth_rate":
            decimal_value = _growth_value(decimal_value, config)
        component_scores.append(
            _normalize(decimal_value, _cohort_values(cohort, field, config), config)
        )
    if not component_scores:
        return None, inputs
    return _component_average(component_scores, config), inputs


def _review_score(
    candidate: SelectionCandidate,
    cohort: Sequence[SelectionCandidate],
    config: SelectionFormulaConfig,
) -> tuple[Decimal | None, dict[str, Decimal | int | None]]:
    inputs: dict[str, Decimal | int | None] = {
        "rating": candidate.rating,
        "review_count": candidate.review_count,
    }
    if candidate.rating is None or candidate.review_count is None or candidate.review_count == 0:
        return None, inputs
    rating_score = (candidate.rating - ONE) / Decimal("4") * HUNDRED
    volume_score = _normalize(
        Decimal(candidate.review_count),
        _cohort_values(cohort, "review_count", config),
        config,
    )
    score = rating_score * config.review_rating_weight + volume_score * config.review_volume_weight
    return _quantize(_clamp(score), config.score_quantum), inputs


def _metric_scores(
    candidate: SelectionCandidate,
    cohort: Sequence[SelectionCandidate],
    profit: ProfitBreakdown,
    config: SelectionFormulaConfig,
) -> dict[SelectionMetric, tuple[Decimal | None, dict[str, Decimal | int | None], str]]:
    demand_score, demand_inputs = _demand_score(candidate, cohort, config)
    review_score, review_inputs = _review_score(candidate, cohort, config)

    competition_score = None
    if candidate.competition_index is not None:
        competition_score = _normalize(
            candidate.competition_index,
            _cohort_values(cohort, "competition_index", config),
            config,
            reverse=True,
        )

    margin_values = [calculate_profit(item, config).margin for item in cohort]
    profitability_score = _normalize(profit.margin, margin_values, config)

    logistics_score = (
        None
        if candidate.logistics_risk_rate is None
        else _fixed_rate_score(candidate.logistics_risk_rate, config, reverse=True)
    )
    after_sales_score = (
        None
        if candidate.after_sales_rate is None
        else _fixed_rate_score(candidate.after_sales_rate, config, reverse=True)
    )
    factory_fit_score = (
        None
        if candidate.factory_fit_score is None
        else _fixed_rate_score(candidate.factory_fit_score, config)
    )

    return {
        SelectionMetric.DEMAND: (
            demand_score,
            demand_inputs,
            "mean(min-max-normalized available demand components within site+currency cohort)",
        ),
        SelectionMetric.COMPETITION: (
            competition_score,
            {"competition_index": candidate.competition_index},
            "100 - min-max(competition_index) within site+currency cohort",
        ),
        SelectionMetric.PROFITABILITY: (
            profitability_score,
            {"profit": profit.profit, "margin": profit.margin},
            "min-max(profit margin) within site+currency cohort",
        ),
        SelectionMetric.REVIEW_QUALITY: (
            review_score,
            review_inputs,
            "80% fixed rating score + 20% cohort-normalized review volume",
        ),
        SelectionMetric.LOGISTICS: (
            logistics_score,
            {"logistics_risk_rate": candidate.logistics_risk_rate},
            "100 * (1 - logistics risk rate)",
        ),
        SelectionMetric.AFTER_SALES: (
            after_sales_score,
            {"after_sales_rate": candidate.after_sales_rate},
            "100 * (1 - after-sales rate)",
        ),
        SelectionMetric.FACTORY_FIT: (
            factory_fit_score,
            {"factory_fit_score": candidate.factory_fit_score},
            "100 * factory-fit proxy score",
        ),
    }


def _build_evidence(
    raw_metrics: Mapping[
        SelectionMetric,
        tuple[Decimal | None, dict[str, Decimal | int | None], str],
    ],
    config: SelectionFormulaConfig,
) -> tuple[dict[SelectionMetric, MetricEvidence], Decimal, Decimal]:
    available_weight = sum(
        (
            config.weights[metric]
            for metric, (score, _, _) in raw_metrics.items()
            if score is not None
        ),
        ZERO,
    )
    if available_weight == ZERO:
        raise ValueError("candidate has no scoreable metrics")

    evidence: dict[SelectionMetric, MetricEvidence] = {}
    weighted_total = ZERO
    for metric, (score, inputs, formula) in raw_metrics.items():
        configured_weight = config.weights[metric]
        effective_weight = (
            ZERO
            if score is None
            else _quantize(configured_weight / available_weight, config.score_quantum)
        )
        if score is not None:
            weighted_total += score * configured_weight / available_weight
        evidence[metric] = MetricEvidence(
            score=score,
            configured_weight=configured_weight,
            effective_weight=effective_weight,
            inputs=inputs,
            formula=formula,
            missing_reason=None if score is not None else "required source metric is unavailable",
        )
    return evidence, _quantize(weighted_total, config.score_quantum), available_weight


def _recommendation_facts(
    score: Decimal,
    profit: ProfitBreakdown,
    metrics: Mapping[SelectionMetric, MetricEvidence],
) -> tuple[str, ...]:
    facts = [
        f"opportunity score {score}",
        f"profit {profit.profit} and margin {profit.margin}",
    ]
    available = [
        (metric.value, evidence.score)
        for metric, evidence in metrics.items()
        if evidence.score is not None
    ]
    if available:
        strongest_name, strongest_score = max(available, key=lambda item: (item[1], item[0]))
        facts.append(f"strongest available metric is {strongest_name} at {strongest_score}")
    return tuple(facts)


def _risk_warnings(
    profit: ProfitBreakdown,
    metrics: Mapping[SelectionMetric, MetricEvidence],
) -> tuple[str, ...]:
    warnings = [
        f"missing {metric.value}: {evidence.missing_reason}"
        for metric, evidence in metrics.items()
        if evidence.score is None
    ]
    if profit.profit < ZERO:
        warnings.append("negative profit")
    if profit.margin < ZERO:
        warnings.append("negative margin")
    return tuple(warnings)


def _score_cohort(
    cohort: Sequence[SelectionCandidate],
    criteria: SelectionCriteria,
    config: SelectionFormulaConfig,
) -> tuple[list[dict[str, object]], list[CandidateExclusion]]:
    eligible: list[tuple[SelectionCandidate, ProfitBreakdown]] = []
    excluded: list[CandidateExclusion] = []
    for candidate in cohort:
        profit = calculate_profit(candidate, config)
        reasons: list[str] = []
        if profit.profit < criteria.minimum_profit:
            reasons.append(f"profit {profit.profit} is below minimum {criteria.minimum_profit}")
        if profit.margin < criteria.minimum_margin:
            reasons.append(f"margin {profit.margin} is below minimum {criteria.minimum_margin}")
        if reasons:
            excluded.append(
                CandidateExclusion(
                    product_id=candidate.product_id,
                    site=candidate.site,
                    currency=candidate.currency,
                    reasons=tuple(reasons),
                    profit=profit,
                    formula_version=config.version,
                )
            )
        else:
            eligible.append((candidate, profit))

    scored: list[dict[str, object]] = []
    eligible_candidates = [candidate for candidate, _ in eligible]
    for candidate, profit in eligible:
        raw_metrics = _metric_scores(candidate, eligible_candidates, profit, config)
        metrics, total_score, available_weight = _build_evidence(raw_metrics, config)
        completeness = _quantize(
            Decimal(sum(item.score is not None for item in metrics.values()))
            / Decimal(len(SelectionMetric)),
            config.score_quantum,
        )
        confidence = _quantize(completeness * available_weight, config.score_quantum)
        scored.append(
            {
                "candidate": candidate,
                "profit": profit,
                "metrics": metrics,
                "total_score": total_score,
                "data_completeness": completeness,
                "confidence": confidence,
            }
        )
    scored.sort(
        key=lambda item: (
            -item["total_score"],
            -item["data_completeness"],
            item["candidate"].product_id,
        )
    )
    return scored, excluded


def score_candidates(
    candidates: Iterable[SelectionCandidate],
    criteria: SelectionCriteria | None = None,
    config: SelectionFormulaConfig = DEFAULT_SELECTION_CONFIG,
) -> SelectionBatchResult:
    criteria = criteria or SelectionCriteria()
    candidate_list = list(candidates)
    product_ids = [candidate.product_id for candidate in candidate_list]
    if len(product_ids) != len(set(product_ids)):
        raise ValueError("product_id must be unique within one scoring batch")

    cohorts: dict[tuple[str, str], list[SelectionCandidate]] = {}
    for candidate in candidate_list:
        cohorts.setdefault(_cohort_key(candidate), []).append(candidate)

    provisional: list[dict[str, object]] = []
    excluded: list[CandidateExclusion] = []
    for cohort_key in sorted(cohorts):
        cohort_scored, cohort_excluded = _score_cohort(
            cohorts[cohort_key],
            criteria,
            config,
        )
        for cohort_rank, item in enumerate(cohort_scored, start=1):
            item["cohort_rank"] = cohort_rank
            provisional.append(item)
        excluded.extend(cohort_excluded)

    provisional.sort(
        key=lambda item: (
            -item["total_score"],
            -item["data_completeness"],
            item["candidate"].site,
            item["candidate"].currency,
            item["candidate"].product_id,
        )
    )
    ranked: list[CandidateScore] = []
    for rank, item in enumerate(provisional, start=1):
        candidate = item["candidate"]
        profit = item["profit"]
        metrics = item["metrics"]
        total_score = item["total_score"]
        ranked.append(
            CandidateScore(
                product_id=candidate.product_id,
                site=candidate.site,
                currency=candidate.currency,
                source_type=candidate.source_type,
                is_mock_data=candidate.is_mock_data,
                rank=rank,
                cohort_rank=item["cohort_rank"],
                total_score=total_score,
                data_completeness=item["data_completeness"],
                confidence=item["confidence"],
                profit=profit,
                metrics=metrics,
                recommendation_facts=_recommendation_facts(total_score, profit, metrics),
                risk_warnings=_risk_warnings(profit, metrics),
                formula_version=config.version,
            )
        )
    excluded.sort(key=lambda item: (item.site, item.currency, item.product_id))
    return SelectionBatchResult(
        formula_version=config.version,
        ranked=tuple(ranked),
        excluded=tuple(excluded),
        cohort_keys=tuple(f"{site}:{currency}" for site, currency in sorted(cohorts)),
    )
