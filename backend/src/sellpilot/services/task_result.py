from __future__ import annotations

from collections.abc import Mapping

from pydantic import JsonValue

from sellpilot.tools.sanitization import audit_summary, redact_nested


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: object, *, limit: int) -> list[object]:
    return list(value)[:limit] if isinstance(value, list) else []


def _review_evidence(value: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in _items(value, limit=2):
        row = _mapping(item)
        rows.append(
            {
                key: row[key]
                for key in (
                    "review_id",
                    "rating",
                    "sentiment",
                    "confidence",
                    "language",
                    "translated_content",
                    "source_created_at",
                )
                if key in row
            }
        )
    return rows


def _review_result(result: Mapping[str, object]) -> dict[str, object]:
    analysis = _mapping(result.get("analysis"))
    topics = []
    for item in _items(analysis.get("topics"), limit=8):
        row = _mapping(item)
        topics.append(
            {
                **{
                    key: row[key]
                    for key in (
                        "topic",
                        "count",
                        "frequency_rate",
                        "negative_count",
                        "severity",
                    )
                    if key in row
                },
                "evidence": _review_evidence(row.get("evidence")),
            }
        )
    pain_points = []
    for item in _items(analysis.get("pain_points"), limit=8):
        row = _mapping(item)
        pain_points.append(
            {
                **{
                    key: row[key]
                    for key in (
                        "pain_point",
                        "frequency_rate",
                        "negative_count",
                        "severity",
                        "affected_sites",
                    )
                    if key in row
                },
                "evidence": _review_evidence(row.get("evidence")),
            }
        )
    return {
        "analysis": {
            key: analysis.get(key)
            for key in (
                "analysis_id",
                "agent_task_id",
                "product_id",
                "site",
                "status",
                "progress",
                "sentiment",
                "quality",
                "no_data",
                "data_source",
                "is_mock_data",
                "analysis_mode",
                "model_version",
                "analyzer_version",
                "finished_at",
            )
        }
        | {
            "topics": topics,
            "pain_points": pain_points,
            "keywords": _items(analysis.get("keywords"), limit=12),
            "trends": _items(analysis.get("trends"), limit=12),
        }
    }


def _selection_result(result: Mapping[str, object]) -> dict[str, object]:
    analysis = _mapping(result.get("analysis"))
    search = _mapping(result.get("candidate_search"))
    return {
        "message": result.get("message"),
        "no_data": result.get("no_data", False),
        "candidate_search": {
            key: search.get(key) for key in ("count", "is_mock_data") if key in search
        },
        "analysis": {
            key: analysis.get(key)
            for key in (
                "task_id",
                "agent_task_id",
                "status",
                "formula_version",
                "generation_mode",
                "total_candidates",
                "ranked_count",
                "excluded_count",
                "is_mock_data",
            )
        }
        | {
            "results": _items(analysis.get("results"), limit=10),
            "excluded": _items(analysis.get("excluded"), limit=10),
        },
    }


def public_task_result(
    workflow_name: str,
    result: object,
) -> dict[str, JsonValue]:
    """Return a bounded, recursively redacted business result for user-facing APIs."""

    source = _mapping(result)
    if workflow_name == "review_analysis":
        projected: object = _review_result(source)
    elif workflow_name == "selection":
        projected = _selection_result(source)
    else:
        projected = source

    bounded = redact_nested(
        projected,
        max_depth=12,
        max_items=30,
        max_string_chars=4_000,
    )
    return audit_summary(bounded, max_bytes=65_536)


__all__ = ["public_task_result"]
