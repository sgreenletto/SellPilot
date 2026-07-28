from pathlib import Path

from sellpilot.evaluation.member3 import evaluate_member3, render_markdown_report

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DATASET = REPOSITORY_ROOT / "data/evaluation/member3/v1/evaluation_cases.json"


async def test_member3_evaluation_is_reproducible_and_exposes_failures() -> None:
    first = await evaluate_member3(DATASET)
    second = await evaluate_member3(DATASET)

    assert first["dataset_version"] == "member3-eval-v1.0.0"
    assert first["failure_count"] == len(first["failures"])
    assert first["metrics"] == second["metrics"]
    assert first["failures"] == second["failures"]
    assert first["metrics"]["selection"]["calculation_correct_rate"] == 1.0
    assert first["metrics"]["selection"]["ranking_stability_rate"] == 1.0
    assert first["metrics"]["content_generation"]["repeat_stability_rate"] == 1.0
    assert first["metrics"]["content_generation"]["provider"] == "offline_template"
    assert first["metrics"]["content_generation"]["token_usage"].startswith("not_applicable")


async def test_member3_evaluation_report_is_generated_from_result() -> None:
    result = await evaluate_member3(DATASET)
    report = render_markdown_report(result)

    assert result["dataset_version"] in report
    assert str(result["failure_count"]) in report
    assert "offline_template" in report
    assert "不伪造数值" in report
