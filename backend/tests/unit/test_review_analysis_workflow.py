import pytest

from sellpilot.core.exceptions import WorkflowFailureError
from sellpilot.domain.review_analysis import ReviewAnalysisReport
from sellpilot.workflows.review_analysis import build_review_analysis_workflow


async def test_review_workflow_retries_until_valid_report():
    attempts = 0

    async def analyzer(reviews):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ValueError("synthetic failure")
        return ReviewAnalysisReport.model_validate(reviews[0])

    payload = {
        "analyzer_version": "test",
        "product_ids": ["P1"],
        "source": {"source_type": "mock", "source_name": "test", "is_mock": True},
        "is_mock_data": True,
        "quality": {
            "received_count": 0,
            "included_count": 0,
            "excluded_count": 0,
            "flag_counts": {},
            "excluded_review_ids": [],
        },
        "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
        "topics": [],
        "pain_points": [],
        "keywords": [],
        "trends": [],
        "judgements": [],
        "facts": [],
    }
    result = await build_review_analysis_workflow(analyzer).ainvoke(
        {
            "reviews": (payload,),
            "max_attempts": 2,
            "attempt_count": 0,
            "report": None,
        }
    )

    assert attempts == 2
    assert result["attempt_count"] == 2
    assert result["report"]["analyzer_version"] == "test"


async def test_review_workflow_exhaustion_is_bounded_and_sanitized():
    attempts = 0

    async def analyzer(_reviews):
        nonlocal attempts
        attempts += 1
        raise RuntimeError("secret raw model response")

    with pytest.raises(WorkflowFailureError) as raised:
        await build_review_analysis_workflow(analyzer).ainvoke(
            {
                "reviews": ({"review_id": "R1"},),
                "max_attempts": 3,
                "attempt_count": 0,
                "report": None,
            }
        )

    assert attempts == 3
    assert "RuntimeError" in str(raised.value)
    assert "secret raw model response" not in str(raised.value)
