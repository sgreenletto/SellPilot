from collections.abc import Awaitable, Callable
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ExplanationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=200)


class SelectionExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1000)
    evidence: list[ExplanationEvidence] = Field(min_length=1, max_length=20)
    risks: list[str] = Field(default_factory=list, max_length=20)
    generation_mode: Literal["rule_template", "validated_generator"]

    @model_validator(mode="after")
    def require_unique_metrics(self) -> "SelectionExplanation":
        metrics = [item.metric for item in self.evidence]
        if len(metrics) != len(set(metrics)):
            raise ValueError("explanation evidence metrics must be unique")
        return self


ExplanationGenerator = Callable[[dict[str, object]], Awaitable[dict[str, object]]]


class SelectionExplanationState(TypedDict):
    score: dict[str, object]
    explanation: dict[str, object] | None


def rule_template_explanation(score: dict[str, object]) -> SelectionExplanation:
    profit = score["profit"]
    evidence = [
        ExplanationEvidence(
            metric="total_score",
            value=str(score["total_score"]),
            source=f"deterministic formula {score['formula_version']}",
        ),
        ExplanationEvidence(
            metric="profit",
            value=str(profit["profit"]),
            source="price minus item, logistics, platform and other costs",
        ),
        ExplanationEvidence(
            metric="margin",
            value=str(profit["margin"]),
            source="profit divided by price",
        ),
        ExplanationEvidence(
            metric="data_completeness",
            value=str(score["data_completeness"]),
            source="available scoring dimensions",
        ),
    ]
    return SelectionExplanation(
        summary="；".join(score["recommendation_facts"]),
        evidence=evidence,
        risks=list(score["risk_warnings"]),
        generation_mode="rule_template",
    )


async def generate_validated_explanation(
    score: dict[str, object],
    generator: ExplanationGenerator | None = None,
    *,
    max_attempts: int = 2,
) -> SelectionExplanation:
    """Validate generated explanations against deterministic evidence, then fall back."""
    if generator is None:
        return rule_template_explanation(score)
    expected = {
        "total_score": str(score["total_score"]),
        "profit": str(score["profit"]["profit"]),
        "margin": str(score["profit"]["margin"]),
        "data_completeness": str(score["data_completeness"]),
    }
    for _ in range(max_attempts):
        try:
            explanation = SelectionExplanation.model_validate(await generator(score))
            supplied = {item.metric: item.value for item in explanation.evidence}
            if any(supplied.get(key) != value for key, value in expected.items()):
                continue
            return explanation.model_copy(update={"generation_mode": "validated_generator"})
        except (ValidationError, TypeError, ValueError):
            continue
    return rule_template_explanation(score)


def build_selection_explanation_workflow(
    generator: ExplanationGenerator | None = None,
):
    """Build the bounded, schema-validated explanation graph."""

    async def generate(state: SelectionExplanationState) -> dict[str, object]:
        explanation = await generate_validated_explanation(
            state["score"], generator, max_attempts=2
        )
        return {"explanation": explanation.model_dump(mode="json")}

    graph = StateGraph(SelectionExplanationState)
    graph.add_node("generate_and_validate", generate)
    graph.add_edge(START, "generate_and_validate")
    graph.add_edge("generate_and_validate", END)
    return graph.compile(name="sellpilot_selection_explanation")
