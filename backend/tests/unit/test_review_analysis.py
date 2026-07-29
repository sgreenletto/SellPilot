import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from sellpilot.core.enums import DataSource, SiteCode
from sellpilot.domain.review_analysis import (
    AnalysisOrigin,
    ReviewAnalysisConfig,
    ReviewAnalysisError,
    ReviewInput,
    ReviewModelError,
    ReviewSentiment,
    ReviewTopic,
    TranslationStatus,
    analyze_reviews,
    classify_review_preview,
)
from sellpilot.domain.review_analysis.models import QualityFlag
from sellpilot.schemas.common import SourceMetadata

SOURCE = SourceMetadata(
    source_type=DataSource.MOCK,
    source_name="simulated_experiment",
    is_mock=True,
)


def review(review_id: str, **overrides) -> ReviewInput:
    values = {
        "review_id": review_id,
        "product_id": "PROD0001",
        "site": SiteCode.SG,
        "rating": 5,
        "content": "Good quality and fast delivery",
        "translated_content": "质量很好，配送很快",
        "declared_language": "English",
        "source_created_at": datetime(2026, 1, 15, tzinfo=UTC),
        "source": SOURCE,
        "source_sentiment_hint": "positive",
        "source_issue_hint": "none",
    }
    values.update(overrides)
    return ReviewInput(**values)


def test_preview_uses_analysis_rules_instead_of_stale_source_hints():
    sentiment, topics = classify_review_preview(
        review(
            "REV-PREVIEW",
            rating=3,
            content="It works as described, though the finish is fairly basic.",
            translated_content="功能符合描述，不过做工比较基础。",
            source_sentiment_hint="neutral",
            source_issue_hint="none",
        )
    )

    assert sentiment == ReviewSentiment.NEGATIVE
    assert ReviewTopic.PRODUCT_QUALITY in topics
    assert ReviewTopic.DESCRIPTION_MISMATCH not in topics


@pytest.mark.parametrize(
    ("language", "content", "expected"),
    [
        ("English", "The item has good quality", "en"),
        ("Filipino", "Maayos ang item pero huli ang delivery", "tl"),
        ("Indonesian", "Produk bagus dan pengiriman cepat", "id"),
        ("Malay", "Produk baik dan penghantaran cepat", "ms"),
        ("Thai", "สินค้าคุณภาพดีแต่จัดส่งช้า", "th"),
        ("Vietnamese", "Sản phẩm tốt và giao hàng nhanh", "vi"),
    ],
)
async def test_detects_six_supported_languages(language, content, expected):
    result = await analyze_reviews([review("REV-1", declared_language=language, content=content)])

    assert result.judgements[0].detected_language == expected
    assert result.quality.included_count == 1


async def test_quality_checks_exclude_empty_emoji_spam_and_duplicate():
    result = await analyze_reviews(
        [
            review("REV-1", content="Good quality"),
            review("REV-2", content="  "),
            review("REV-3", content="😍🔥"),
            review("REV-4", content="CLICK HERE https://spam.invalid"),
            review("REV-5", content=" good   quality "),
        ]
    )

    assert result.quality.received_count == 5
    assert result.quality.included_count == 1
    assert result.quality.excluded_review_ids == (
        "REV-2",
        "REV-3",
        "REV-4",
        "REV-5",
    )
    assert result.quality.flag_counts[QualityFlag.DUPLICATE] == 1
    assert result.quality.flag_counts[QualityFlag.EMPTY] == 1
    assert result.quality.flag_counts[QualityFlag.EMOJI_ONLY] == 1
    assert result.quality.flag_counts[QualityFlag.SPAM] == 1


async def test_unknown_language_and_translation_unavailable_are_explicit():
    result = await analyze_reviews(
        [
            review(
                "REV-1",
                content="xyz qqq zzz",
                translated_content=None,
                declared_language=None,
            )
        ]
    )

    judgement = result.judgements[0]
    assert judgement.detected_language == "unknown"
    assert judgement.translation_status == TranslationStatus.UNAVAILABLE
    assert QualityFlag.UNKNOWN_LANGUAGE in judgement.quality_flags
    assert judgement.confidence < Decimal("0.82")


async def test_long_text_is_truncated_for_analysis_but_preserved_as_evidence():
    original = "quality " * 800
    config = ReviewAnalysisConfig(version="test", maximum_content_length=100)

    result = await analyze_reviews([review("REV-1", content=original)], config=config)

    judgement = result.judgements[0]
    assert QualityFlag.TRUNCATED in judgement.quality_flags
    assert judgement.original_content == original


async def test_sentiment_topics_evidence_and_trends_reconcile():
    result = await analyze_reviews(
        [
            review(
                "REV-1",
                rating=1,
                content="Broken product and damaged packaging",
                source_created_at=datetime(2026, 1, 2, tzinfo=UTC),
            ),
            review(
                "REV-2",
                rating=3,
                content="The item is acceptable",
                translated_content=None,
                source_created_at=datetime(2026, 1, 10, tzinfo=UTC),
            ),
            review(
                "REV-3",
                rating=5,
                content="Good quality and fast delivery",
                site=SiteCode.MY,
                source_created_at=datetime(2026, 2, 1, tzinfo=UTC),
            ),
        ]
    )

    assert result.sentiment.negative == 1
    assert result.sentiment.neutral == 1
    assert result.sentiment.positive == 1
    quality = next(
        aggregate for aggregate in result.topics if aggregate.topic == ReviewTopic.PRODUCT_QUALITY
    )
    assert quality.count == 2
    assert quality.negative_count == 1
    assert quality.evidence[0].review_id == "REV-1"
    assert result.pain_points[0].evidence[0].review_id == "REV-1"
    assert result.pain_points[0].negative_count >= 1
    assert any(keyword.keyword == "quality" for keyword in result.keywords)
    assert all(
        set(keyword.review_ids) <= {"REV-1", "REV-2", "REV-3"} for keyword in result.keywords
    )
    assert {(point.site, point.month) for point in result.trends} == {
        (SiteCode.SG, "2026-01"),
        (SiteCode.MY, "2026-02"),
    }


async def test_multitopic_review_keeps_all_allowed_topics():
    result = await analyze_reviews(
        [
            review(
                "REV-1",
                rating=1,
                content="Wrong item, damaged packaging, and delivery was late",
            )
        ]
    )

    topics = set(result.judgements[0].topics)
    assert ReviewTopic.WRONG_OR_MISSING_ITEM in topics
    assert ReviewTopic.PACKAGING in topics
    assert ReviewTopic.LOGISTICS in topics


async def test_no_analyzable_reviews_fails_instead_of_returning_empty_success():
    with pytest.raises(ReviewAnalysisError, match="no analyzable"):
        await analyze_reviews([review("REV-1", content="😍")])


async def test_empty_input_and_duplicate_ids_fail():
    with pytest.raises(ReviewAnalysisError, match="at least one"):
        await analyze_reviews([])
    with pytest.raises(ValueError, match="review_id must be unique"):
        await analyze_reviews([review("REV-1"), review("REV-1", content="Different")])


class FakeModel:
    def __init__(self, output):
        self.output = output

    async def analyze(self, reviews):
        return self.output


async def test_fake_model_valid_output_is_schema_checked_and_attributed():
    model = FakeModel(
        {
            "labels": [
                {
                    "review_id": "REV-1",
                    "sentiment": "negative",
                    "topics": ["material", "size_specification"],
                    "confidence": "0.91",
                }
            ]
        }
    )

    result = await analyze_reviews([review("REV-1", rating=2)], model=model)

    judgement = result.judgements[0]
    assert judgement.origin == AnalysisOrigin.MODEL
    assert judgement.sentiment == ReviewSentiment.NEGATIVE
    assert judgement.topics == (
        ReviewTopic.MATERIAL,
        ReviewTopic.SIZE_SPECIFICATION,
    )


@pytest.mark.parametrize(
    "output",
    [
        "not json",
        {"labels": [{"review_id": "REV-1", "sentiment": "negative"}]},
        {
            "labels": [
                {
                    "review_id": "REV-1",
                    "sentiment": "negative",
                    "topics": ["unknown_topic"],
                    "confidence": 1,
                }
            ]
        },
        {
            "labels": [
                {
                    "review_id": "NOT-IN-INPUT",
                    "sentiment": "negative",
                    "topics": ["other"],
                    "confidence": 1,
                }
            ]
        },
        {"labels": []},
        {
            "labels": [
                {
                    "review_id": "REV-1",
                    "sentiment": "negative",
                    "topics": ["other"],
                    "confidence": "0.10",
                }
            ]
        },
    ],
)
async def test_invalid_model_outputs_fail_closed(output):
    with pytest.raises(ReviewModelError):
        await analyze_reviews([review("REV-1")], model=FakeModel(output))


class SlowModel:
    async def analyze(self, reviews):
        await asyncio.sleep(0.05)
        return {"labels": []}


async def test_model_timeout_fails_closed():
    config = ReviewAnalysisConfig(
        version="timeout-test",
        model_timeout_seconds=Decimal("0.01"),
    )
    with pytest.raises(ReviewModelError, match="timed out"):
        await analyze_reviews([review("REV-1")], model=SlowModel(), config=config)


class FakeTranslator:
    async def translate(self, text, *, source_language, target_language):
        assert source_language == "th"
        assert target_language == "zh-CN"
        return "配送速度较慢"


class FailingTranslator:
    async def translate(self, text, *, source_language, target_language):
        raise RuntimeError("offline translator failed")


async def test_optional_translator_success_is_used_and_preserved_as_evidence():
    result = await analyze_reviews(
        [
            review(
                "REV-1",
                content="จัดส่งช้า",
                translated_content=None,
                declared_language="Thai",
            )
        ],
        translator=FakeTranslator(),
    )

    judgement = result.judgements[0]
    assert judgement.translation_status == TranslationStatus.PROVIDED
    assert judgement.translated_content == "配送速度较慢"
    assert judgement.display_content == "配送速度较慢"


async def test_translation_failure_preserves_original_and_marks_status():
    original = "จัดส่งช้า"
    result = await analyze_reviews(
        [
            review(
                "REV-1",
                content=original,
                translated_content=None,
                declared_language="Thai",
            )
        ],
        translator=FailingTranslator(),
    )

    judgement = result.judgements[0]
    assert judgement.translation_status == TranslationStatus.FAILED
    assert judgement.translated_content is None
    assert judgement.display_content == original


async def test_source_hints_do_not_override_rating_or_evidence_rules():
    result = await analyze_reviews(
        [
            review(
                "REV-1",
                rating=1,
                content="The item failed",
                source_sentiment_hint="positive",
                source_issue_hint="none",
            )
        ]
    )

    judgement = result.judgements[0]
    assert judgement.sentiment == ReviewSentiment.NEGATIVE
    assert judgement.origin == AnalysisOrigin.RULE


@pytest.mark.asyncio
async def test_positive_description_matches_are_not_mislabeled_as_mismatch():
    result = await analyze_reviews(
        [
            review(
                "REV-POSITIVE-MATCH",
                rating=5,
                content="The color matches the photos and it works as described.",
                translated_content="颜色与图片一致，功能符合描述。",
                source_issue_hint="description_mismatch",
            )
        ]
    )

    assert ReviewTopic.DESCRIPTION_MISMATCH not in result.judgements[0].topics
    assert result.judgements[0].sentiment == ReviewSentiment.POSITIVE


@pytest.mark.asyncio
async def test_positive_finish_and_size_mentions_are_not_improvement_signals():
    result = await analyze_reviews(
        [
            review(
                "REV-POSITIVE-FINISH-SIZE",
                rating=5,
                content="The finish is clean and the size is exactly right for me.",
                translated_content="做工整洁，尺寸对我来说正合适。",
            )
        ]
    )

    judgement = result.judgements[0]
    assert judgement.sentiment == ReviewSentiment.POSITIVE
    assert ReviewTopic.PRODUCT_QUALITY in judgement.topics
    assert ReviewTopic.SIZE_SPECIFICATION in judgement.topics
    assert result.pain_points == ()


@pytest.mark.asyncio
async def test_three_star_review_with_explicit_drawback_is_negative_evidence():
    result = await analyze_reviews(
        [
            review(
                "REV-MIXED",
                rating=3,
                content="Delivery took the usual time; I hope the next batch improves.",
            )
        ]
    )

    judgement = result.judgements[0]
    assert judgement.sentiment == ReviewSentiment.NEGATIVE
    assert ReviewTopic.LOGISTICS in judgement.topics
    assert result.pain_points[0].pain_point == ReviewTopic.LOGISTICS
