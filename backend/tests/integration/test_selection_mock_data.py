import csv
from decimal import Decimal
from pathlib import Path

from sellpilot.core.enums import CurrencyCode, DataSource, SiteCode
from sellpilot.domain.selection import SelectionCandidate, score_candidates
from sellpilot.schemas.common import SourceMetadata

MOCK_DATA_ROOT = Path(__file__).resolve().parents[3] / "data" / "demo" / "shopee_mock"
SITE_CODES = {
    "Singapore": SiteCode.SG,
    "Malaysia": SiteCode.MY,
    "Philippines": SiteCode.PH,
    "Thailand": SiteCode.TH,
    "Vietnam": SiteCode.VN,
    "Indonesia": SiteCode.ID,
}


def test_all_mock_products_match_selection_input_contract():
    with (MOCK_DATA_ROOT / "products.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    candidates = [
        SelectionCandidate(
            product_id=row["product_id"],
            site=SITE_CODES[row["site"]],
            currency=CurrencyCode(row["currency"]),
            source=SourceMetadata(
                source_type=DataSource.MOCK,
                source_name=row["source_type"],
                is_mock=row["is_mock_data"].lower() == "true",
            ),
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

    assert len(candidates) == 103
    assert len(result.ranked) + len(result.excluded) == 103
    assert {item.product_id for item in candidates if item.site is SiteCode.SG} >= {
        "PROD0101",
        "PROD0102",
        "PROD0103",
    }
    assert result.cohort_keys == (
        "id:IDR",
        "my:MYR",
        "ph:PHP",
        "sg:SGD",
        "th:THB",
        "vn:VND",
    )
    assert all(item.source.is_mock for item in result.ranked)
