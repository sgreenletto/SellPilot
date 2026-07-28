from collections.abc import Awaitable, Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from sellpilot.core.exceptions import WorkflowFailureError
from sellpilot.domain.review_analysis import ReviewAnalysisReport, ReviewInput, analyze_reviews

ReviewAnalyzer = Callable[[tuple[ReviewInput, ...]], Awaitable[ReviewAnalysisReport]]


class ReviewAnalysisState(TypedDict):
    reviews: tuple[ReviewInput, ...]
    max_attempts: int
    attempt_count: int
    report: dict[str, object] | None


def build_review_analysis_workflow(
    analyzer: ReviewAnalyzer = analyze_reviews,
):
    async def validate_input(state: ReviewAnalysisState) -> dict[str, object]:
        if not state["reviews"]:
            raise WorkflowFailureError("Review analysis requires at least one review")
        return {"attempt_count": state.get("attempt_count", 0)}

    async def analyze_with_retry(state: ReviewAnalysisState) -> dict[str, object]:
        last_error: Exception | None = None
        attempts = state.get("attempt_count", 0)
        while attempts < state["max_attempts"]:
            attempts += 1
            try:
                report = await analyzer(state["reviews"])
                return {
                    "attempt_count": attempts,
                    "report": report.model_dump(mode="json"),
                }
            except Exception as exc:
                last_error = exc
        raise WorkflowFailureError(
            f"Review analysis failed after {attempts} attempt(s): "
            f"{type(last_error).__name__ if last_error else 'unknown'}"
        ) from last_error

    graph = StateGraph(ReviewAnalysisState)
    graph.add_node("validate_input", validate_input)
    graph.add_node("analyze_with_retry", analyze_with_retry)
    graph.add_edge(START, "validate_input")
    graph.add_edge("validate_input", "analyze_with_retry")
    graph.add_edge("analyze_with_retry", END)
    return graph.compile(name="sellpilot_review_analysis")
