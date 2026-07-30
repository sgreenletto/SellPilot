from sellpilot.cli.check_demo_readiness import (
    CORE_QUERIES,
    classify_knowledge_readiness,
    classify_readiness,
)


def _counts(value: int = 1) -> dict[str, int]:
    return dict.fromkeys(CORE_QUERIES, value)


def test_readiness_is_blocked_when_core_data_is_missing() -> None:
    counts = _counts()
    counts["orders"] = 0

    assert classify_readiness(counts, indexed_documents=1, indexed_chunks=1) == "NOT_READY"


def test_readiness_distinguishes_missing_rag_data() -> None:
    assert (
        classify_readiness(_counts(), indexed_documents=0, indexed_chunks=0) == "BLOCKED_RAG_DATA"
    )


def test_readiness_does_not_treat_mock_only_knowledge_as_real_data() -> None:
    assert classify_knowledge_readiness(real_documents=0, real_chunks=0) == "BLOCKED_RAG_DATA"


def test_readiness_is_ready_with_core_and_knowledge_data() -> None:
    assert classify_readiness(_counts(), indexed_documents=1, indexed_chunks=1) == "READY"


def test_market_readiness_uses_product_snapshot_query() -> None:
    query = CORE_QUERIES["market_products"]

    assert '"products"' in query
    assert "selection_candidates" not in query
