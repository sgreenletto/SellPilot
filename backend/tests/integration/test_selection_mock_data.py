import csv
from decimal import Decimal
from pathlib import Path

from sellpilot.domain.selection import SelectionCandidate, score_candidates

MOCK_DATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "demo" / "shopee_mock"


def test_all_mock_products_match_selection_input_contract():
    with (MOCK_DATA_ROOT / "products.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    candidates = [
        SelectionCandidate(
            product_id=row["product_id"],
            site=row["site"],
            currency=row["currency"],
            source_type=row["source_type"],
            is_mock_data=row["is_mock_data"].lower() == "true",
            price=Decimal(row["price"]),
            cost=Decimal(row["cost"]),
            shipping_cost=Decimal(row["shipping_cost"]),
            sales_count=int(row["sales_count"]),
            rating=Decimal(row["rating"]),
            review_count=int(row["review_count"]),
        )
        for row in rows
    ]

    result = score_candidates(candidates)

    assert len(candidates) == 100
    assert len(result.ranked) + len(result.excluded) == 100
    assert result.cohort_keys == (
        "Indonesia:IDR",
        "Malaysia:MYR",
        "Philippines:PHP",
        "Singapore:SGD",
        "Thailand:THB",
        "Vietnam:VND",
    )
    assert all(item.is_mock_data for item in result.ranked)
