import json
from asyncio import to_thread
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any

from sellpilot.core.enums import DataSource
from sellpilot.domain.content_generation.models import ListingFacts, LocalizedListing
from sellpilot.domain.content_generation.workflow import check_listing, generate_with_quality_loop
from sellpilot.domain.review_analysis.analyzer import analyze_reviews
from sellpilot.domain.review_analysis.models import ReviewInput
from sellpilot.domain.selection.models import SelectionCandidate
from sellpilot.domain.selection.scoring import calculate_profit, score_candidates
from sellpilot.schemas.common import SourceMetadata
from sellpilot.services.model_gateway import OfflineTemplateGateway

EVALUATION_VERSION = "member3-evaluator-v1.0.0"
PROMPT_VERSION = "offline-template-v1"


def _mock_source(reference: str) -> SourceMetadata:
    return SourceMetadata(
        source_type=DataSource.MOCK,
        source_name="member3-versioned-evaluation",
        source_reference=reference,
        is_mock=True,
        generated_at=datetime(2026, 7, 28, tzinfo=UTC),
    )


def _rate(passed: int, total: int) -> float:
    return round(passed / total, 4) if total else 0.0


def _failure(
    *,
    case_id: str,
    capability: str,
    input_value: object,
    expected: object,
    actual: object,
    failure_type: str,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "capability": capability,
        "input": input_value,
        "expected": expected,
        "actual": actual,
        "model_or_formula_version": PROMPT_VERSION,
        "failure_type": failure_type,
        "fixed": False,
        "regression_test_id": case_id,
    }


def _evaluate_selection(cases: list[dict[str, Any]]) -> tuple[dict[str, object], list[dict]]:
    failures: list[dict] = []
    candidates: list[SelectionCandidate] = []
    correct = 0
    for case in cases:
        candidate = SelectionCandidate(
            **case["candidate"],
            source=_mock_source(case["id"]),
        )
        candidates.append(candidate)
        actual = calculate_profit(candidate)
        expected = case["expected"]
        passed = actual.profit == Decimal(expected["profit"]) and actual.margin == Decimal(
            expected["margin"]
        )
        correct += int(passed)
        if not passed:
            failures.append(
                _failure(
                    case_id=case["id"],
                    capability="selection_profit",
                    input_value=case["candidate"],
                    expected=expected,
                    actual=actual.model_dump(mode="json"),
                    failure_type="calculation_mismatch",
                )
            )
    first = score_candidates(candidates)
    second = score_candidates(list(reversed(candidates)))
    first_order = [row.product_id for row in first.ranked]
    second_order = [row.product_id for row in second.ranked]
    stable = first_order == second_order
    if not stable:
        failures.append(
            _failure(
                case_id="SEL-STABILITY-001",
                capability="selection_ranking",
                input_value=[item.model_dump(mode="json") for item in candidates],
                expected=first_order,
                actual=second_order,
                failure_type="non_deterministic_order",
            )
        )
    return {
        "calculation_correct_rate": _rate(correct, len(cases)),
        "ranking_stability_rate": 1.0 if stable else 0.0,
        "formula_version": first.formula_version,
        "case_count": len(cases),
    }, failures


async def _evaluate_reviews(
    cases: list[dict[str, Any]],
) -> tuple[dict[str, object], list[dict]]:
    failures: list[dict] = []
    reviews = [
        ReviewInput(
            review_id=case["id"],
            product_id="EVAL-PROD-REVIEWS",
            site="sg",
            rating=case["rating"],
            content=case["content"],
            declared_language="en",
            source_created_at=datetime(2026, 7, index + 1, tzinfo=UTC),
            source=_mock_source("member3-review-evaluation"),
        )
        for index, case in enumerate(cases)
    ]
    report = await analyze_reviews(reviews)
    by_id = {row.review_id: row for row in report.judgements}
    sentiment_correct = 0
    topic_correct = 0
    evidence_valid = 0
    for case in cases:
        actual = by_id[case["id"]]
        sentiment_passed = actual.sentiment.value == case["expected_sentiment"]
        topic_passed = case["expected_topic"] in {topic.value for topic in actual.topics}
        sentiment_correct += int(sentiment_passed)
        topic_correct += int(topic_passed)
        if not sentiment_passed or not topic_passed:
            failures.append(
                _failure(
                    case_id=case["id"],
                    capability="review_analysis",
                    input_value={"rating": case["rating"], "content": case["content"]},
                    expected={
                        "sentiment": case["expected_sentiment"],
                        "topic": case["expected_topic"],
                    },
                    actual={
                        "sentiment": actual.sentiment.value,
                        "topics": [topic.value for topic in actual.topics],
                    },
                    failure_type="classification_mismatch",
                )
            )
    known_ids = set(by_id)
    references = [evidence.review_id for topic in report.topics for evidence in topic.evidence] + [
        evidence.review_id for pain_point in report.pain_points for evidence in pain_point.evidence
    ]
    evidence_valid = sum(reference in known_ids for reference in references)
    return {
        "sentiment_correct_rate": _rate(sentiment_correct, len(cases)),
        "topic_correct_rate": _rate(topic_correct, len(cases)),
        "evidence_reference_valid_rate": _rate(evidence_valid, len(references)),
        "analysis_origin": "rule",
        "analyzer_version": report.analyzer_version,
        "case_count": len(cases),
    }, failures


async def _evaluate_content(
    cases: list[dict[str, Any]],
    compliance_cases: list[dict[str, Any]],
) -> tuple[dict[str, object], list[dict]]:
    failures: list[dict] = []
    gateway = OfflineTemplateGateway()
    structured = facts_consistent = stable = multilingual = 0
    for case in cases:
        facts = ListingFacts.model_validate(case["facts"])
        first = await generate_with_quality_loop(gateway, facts)
        second = await generate_with_quality_loop(gateway, facts)
        structured += int(isinstance(first.content, LocalizedListing))
        fact_passed = not first.quality.fact_issues
        facts_consistent += int(fact_passed)
        stable += int(first.model_dump(mode="json") == second.model_dump(mode="json"))
        multilingual += int(first.content.target_language == facts.target_language)
        expected = case["expected"]
        passed = (
            first.quality.passed is expected["quality_passed"]
            and first.content.generation_mode == expected["generation_mode"]
        )
        if not passed:
            failures.append(
                _failure(
                    case_id=case["id"],
                    capability="content_generation",
                    input_value=case["facts"],
                    expected=expected,
                    actual=first.model_dump(mode="json"),
                    failure_type="quality_or_schema_mismatch",
                )
            )

    compliance_detected = 0
    compliance_correct = 0
    base_facts = ListingFacts.model_validate(cases[0]["facts"])
    base_content = await gateway.generate(base_facts)
    for case in compliance_cases:
        candidate = base_content.model_copy(update={"marketing_copy": case["claim"]})
        result = check_listing(candidate, base_facts, 1)
        detected = bool(result.compliance_issues)
        compliance_detected += int(detected)
        correct = detected is case["expected_detected"]
        compliance_correct += int(correct)
        if not correct:
            failures.append(
                _failure(
                    case_id=case["id"],
                    capability="content_compliance",
                    input_value=case["claim"],
                    expected=case["expected_detected"],
                    actual=detected,
                    failure_type="compliance_detection_mismatch",
                )
            )
    total = len(cases)
    return {
        "structured_output_success_rate": _rate(structured, total),
        "fact_consistency_rate": _rate(facts_consistent, total),
        "hallucination_rate": round(1 - _rate(facts_consistent, total), 4),
        "multilingual_schema_score": _rate(multilingual, total),
        "repeat_stability_rate": _rate(stable, total),
        "compliance_detection_accuracy": _rate(compliance_correct, len(compliance_cases)),
        "detected_claim_count": compliance_detected,
        "provider": gateway.provider,
        "model_name": gateway.model_name,
        "prompt_version": PROMPT_VERSION,
        "token_usage": "not_applicable_offline_provider",
        "estimated_cost": "not_applicable_offline_provider",
        "case_count": total,
    }, failures


async def evaluate_member3(dataset_path: Path) -> dict[str, object]:
    started = perf_counter()
    dataset_text = await to_thread(dataset_path.read_text, encoding="utf-8")
    dataset = json.loads(dataset_text)
    selection, selection_failures = _evaluate_selection(deepcopy(dataset["selection"]))
    reviews, review_failures = await _evaluate_reviews(deepcopy(dataset["reviews"]))
    content, content_failures = await _evaluate_content(
        deepcopy(dataset["content"]),
        deepcopy(dataset["compliance"]),
    )
    failures = [*selection_failures, *review_failures, *content_failures]
    split_counts: dict[str, int] = {}
    for group in ("selection", "reviews", "content", "compliance"):
        for case in dataset[group]:
            split_counts[case["split"]] = split_counts.get(case["split"], 0) + 1
    return {
        "evaluator_version": EVALUATION_VERSION,
        "dataset_version": dataset["dataset_version"],
        "generated_at": datetime.now(UTC).isoformat(),
        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
        "split_counts": dict(sorted(split_counts.items())),
        "metrics": {
            "selection": selection,
            "review_analysis": reviews,
            "content_generation": content,
        },
        "failure_count": len(failures),
        "failures": failures,
    }


def render_markdown_report(result: dict[str, object]) -> str:
    lines = [
        "# 成员三 AI 能力评估报告",
        "",
        f"- 数据集版本：`{result['dataset_version']}`",
        f"- 评估器版本：`{result['evaluator_version']}`",
        f"- 实际运行时间：`{result['generated_at']}`",
        f"- 总耗时：`{result['elapsed_ms']} ms`",
        f"- 失败案例：`{result['failure_count']}`",
        "",
        "## 实际指标",
        "",
    ]
    metrics = result["metrics"]
    for capability, values in metrics.items():
        lines.extend([f"### {capability}", ""])
        for name, value in values.items():
            lines.append(f"- {name}: `{value}`")
        lines.append("")
    lines.extend(["## 失败案例", ""])
    failures = result["failures"]
    if not failures:
        lines.append("本次固定评估集未发现失败案例。评估器不会隐藏后续新增案例的失败。")
    else:
        for failure in failures:
            lines.extend(
                [
                    f"### {failure['case_id']}",
                    "",
                    f"- 能力：`{failure['capability']}`",
                    f"- 类型：`{failure['failure_type']}`",
                    f"- 模型/公式版本：`{failure['model_or_formula_version']}`",
                    f"- 已修复：`{failure['fixed']}`",
                    f"- 回归测试：`{failure['regression_test_id']}`",
                    f"- 期望：`{json.dumps(failure['expected'], ensure_ascii=False)}`",
                    f"- 实际：`{json.dumps(failure['actual'], ensure_ascii=False)}`",
                    "",
                ]
            )
    lines.extend(
        [
            "## 边界说明",
            "",
            "- 数据全部为固定合成数据，不包含真实用户或店铺数据。",
            "- 内容生成使用明确标记的 `offline_template`，未冒充真实 LLM。",
            "- 离线提供方没有 Token 和计费，因此相关字段记录为不适用，不伪造数值。",
            "",
        ]
    )
    return "\n".join(lines)
