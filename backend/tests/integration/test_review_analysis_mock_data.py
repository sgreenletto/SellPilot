import csv
from datetime import datetime
from pathlib import Path

import pytest

from sellpilot.core.enums import DataSource, SiteCode
from sellpilot.domain.review_analysis import ReviewInput, analyze_reviews
from sellpilot.schemas.common import SourceMetadata

ROOT = Path(__file__).resolve().parents[3]
REVIEWS_FILE = ROOT / "data" / "demo" / "shopee_mock" / "reviews.csv"
PRODUCTS_FILE = ROOT / "data" / "demo" / "shopee_mock" / "products.csv"
SOURCE = SourceMetadata(
    source_type=DataSource.MOCK,
    source_name="shopee_mock",
    source_reference="data/demo/shopee_mock/reviews.csv",
    is_mock=True,
)
SITE_MAP = {
    "Singapore": SiteCode.SG,
    "Malaysia": SiteCode.MY,
    "Philippines": SiteCode.PH,
    "Thailand": SiteCode.TH,
    "Vietnam": SiteCode.VN,
    "Indonesia": SiteCode.ID,
}


@pytest.mark.skipif(not REVIEWS_FILE.exists(), reason="mock review package is unavailable")
async def test_complete_mock_review_package_is_analyzable_and_evidence_bound():
    with PRODUCTS_FILE.open(encoding="utf-8-sig", newline="") as handle:
        products = {row["product_id"]: SITE_MAP[row["site"]] for row in csv.DictReader(handle)}
    with REVIEWS_FILE.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    inputs = [
        ReviewInput(
            review_id=row["review_id"],
            product_id=row["product_id"],
            site=products[row["product_id"]],
            rating=int(row["rating"]),
            content=row["content"],
            translated_content=row["content_zh"],
            declared_language=row["language"],
            source_created_at=datetime.fromisoformat(row["created_at"]),
            source=SOURCE,
            source_sentiment_hint=row["sentiment_hint"],
            source_issue_hint=row["issue_type"],
        )
        for row in rows
    ]

    report = await analyze_reviews(inputs)

    assert report.quality.received_count == 1000
    assert report.quality.included_count > 0
    assert report.quality.included_count + report.quality.excluded_count == 1000
    assert report.is_mock_data is True
    assert {item.site for item in report.judgements} == set(SITE_MAP.values())
    input_ids = {item.review_id for item in inputs}
    evidence_ids = {
        evidence.review_id for aggregate in report.topics for evidence in aggregate.evidence
    }
    assert evidence_ids
    assert evidence_ids <= input_ids
    assert report.pain_points
    assert all(item.evidence for item in report.pain_points)
    assert report.keywords
    assert all(set(item.review_ids) <= input_ids for item in report.keywords)
    assert sum(report.sentiment.model_dump().values()) == len(report.judgements)
