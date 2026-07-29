from sellpilot.services.task_result import public_task_result


def test_review_public_result_is_bounded_and_excludes_full_judgements() -> None:
    result = public_task_result(
        "review_analysis",
        {
            "analysis": {
                "product_id": "PROD0001",
                "no_data": False,
                "quality": {"included_count": 16},
                "sentiment": {"positive": 8, "neutral": 3, "negative": 5},
                "topics": [
                    {
                        "topic": "product_quality",
                        "count": 3,
                        "evidence": [
                            {
                                "review_id": "REV001",
                                "rating": 3,
                                "sentiment": "negative",
                                "translated_content": "做工比较基础。",
                                "original_content": "The finish is basic.",
                            }
                        ],
                    }
                ],
                "pain_points": [],
                "judgements": [
                    {
                        "review_id": f"REV{index:03d}",
                        "original_content": "raw review " * 500,
                    }
                    for index in range(30)
                ],
            }
        },
    )

    analysis = result["analysis"]
    assert isinstance(analysis, dict)
    assert analysis["product_id"] == "PROD0001"
    assert "judgements" not in analysis
    evidence = analysis["topics"][0]["evidence"][0]
    assert evidence["translated_content"] == "做工比较基础。"
    assert "original_content" not in evidence
    assert result.get("truncated") is not True


def test_selection_public_result_keeps_top_n_and_drops_candidate_payload() -> None:
    result = public_task_result(
        "selection",
        {
            "no_data": False,
            "candidate_search": {
                "count": 20,
                "is_mock_data": True,
                "products": [{"description": "large payload"} for _ in range(20)],
            },
            "analysis": {
                "ranked_count": 20,
                "total_candidates": 20,
                "results": [
                    {"product_id": f"PROD{index:04d}", "rank": index} for index in range(20)
                ],
                "excluded": [],
            },
        },
    )

    search = result["candidate_search"]
    analysis = result["analysis"]
    assert isinstance(search, dict)
    assert "products" not in search
    assert isinstance(analysis, dict)
    assert len(analysis["results"]) == 10
