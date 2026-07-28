import asyncio
import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import ValidationError

from sellpilot.domain.review_analysis.models import (
    AnalysisOrigin,
    EvidenceReference,
    KeywordAggregate,
    ModelBatchOutput,
    ModelReviewLabel,
    PainPointAggregate,
    PreparedReview,
    QualityFlag,
    QualityReport,
    ReviewAnalysisConfig,
    ReviewAnalysisReport,
    ReviewInput,
    ReviewJudgement,
    ReviewModel,
    ReviewSentiment,
    ReviewTopic,
    ReviewTranslator,
    SentimentAggregate,
    TopicAggregate,
    TranslationStatus,
    TrendPoint,
)
from sellpilot.domain.review_analysis.preprocessing import prepare_reviews

ZERO = Decimal("0")
ONE = Decimal("1")
FOUR = Decimal("4")
QUANTUM = Decimal("0.0001")

DEFAULT_REVIEW_ANALYSIS_CONFIG = ReviewAnalysisConfig(version="review-analysis-v1.0.0")

TOPIC_KEYWORDS: dict[ReviewTopic, tuple[str, ...]] = {
    ReviewTopic.PRODUCT_QUALITY: (
        "quality",
        "broken",
        "defect",
        "damaged",
        "kualitas",
        "rosak",
        "คุณภาพ",
        "เสีย",
        "chất lượng",
        "hỏng",
        "质量",
        "损坏",
    ),
    ReviewTopic.PACKAGING: (
        "packaging",
        "package",
        "box",
        "kemasan",
        "bungkusan",
        "บรรจุ",
        "hộp",
        "đóng gói",
        "包装",
    ),
    ReviewTopic.DESCRIPTION_MISMATCH: (
        "not as described",
        "different from",
        "picture",
        "description",
        "tidak sesuai",
        "tak sama",
        "ไม่ตรง",
        "không giống",
        "描述",
        "图片",
    ),
    ReviewTopic.LOGISTICS: (
        "delivery",
        "shipping",
        "late",
        "courier",
        "pengiriman",
        "penghantaran",
        "huli",
        "จัดส่ง",
        "ส่งช้า",
        "giao hàng",
        "配送",
        "物流",
    ),
    ReviewTopic.SERVICE: (
        "service",
        "seller",
        "reply",
        "support",
        "layanan",
        "perkhidmatan",
        "serbisyo",
        "บริการ",
        "dịch vụ",
        "客服",
        "服务",
    ),
    ReviewTopic.MATERIAL: (
        "material",
        "plastic",
        "fabric",
        "bahan",
        "materyal",
        "วัสดุ",
        "chất liệu",
        "材料",
    ),
    ReviewTopic.SIZE_SPECIFICATION: (
        "size",
        "small",
        "large",
        "measurement",
        "ukuran",
        "saiz",
        "sukat",
        "ขนาด",
        "kích thước",
        "尺寸",
        "规格",
    ),
    ReviewTopic.WRONG_OR_MISSING_ITEM: (
        "wrong item",
        "missing item",
        "incomplete",
        "salah barang",
        "kurang",
        "maling item",
        "ผิดชิ้น",
        "thiếu",
        "sai hàng",
        "错发",
        "漏发",
    ),
}

ISSUE_HINT_TOPICS = {
    "product": ReviewTopic.PRODUCT_QUALITY,
    "quality": ReviewTopic.PRODUCT_QUALITY,
    "packaging": ReviewTopic.PACKAGING,
    "description": ReviewTopic.DESCRIPTION_MISMATCH,
    "description_mismatch": ReviewTopic.DESCRIPTION_MISMATCH,
    "logistics": ReviewTopic.LOGISTICS,
    "service": ReviewTopic.SERVICE,
    "material": ReviewTopic.MATERIAL,
    "size": ReviewTopic.SIZE_SPECIFICATION,
    "specification": ReviewTopic.SIZE_SPECIFICATION,
    "wrong_item": ReviewTopic.WRONG_OR_MISSING_ITEM,
    "missing_item": ReviewTopic.WRONG_OR_MISSING_ITEM,
}


class ReviewAnalysisError(ValueError):
    pass


class ReviewModelError(ReviewAnalysisError):
    pass


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(QUANTUM, rounding=ROUND_HALF_UP)


def _sentiment_from_rating(rating: int) -> ReviewSentiment:
    if rating >= 4:
        return ReviewSentiment.POSITIVE
    if rating == 3:
        return ReviewSentiment.NEUTRAL
    return ReviewSentiment.NEGATIVE


def _rule_topics(item: PreparedReview) -> tuple[ReviewTopic, ...]:
    text = f"{item.normalized_content} {item.analysis_content}".casefold()
    topics = {
        topic
        for topic, keywords in TOPIC_KEYWORDS.items()
        if any(keyword.casefold() in text for keyword in keywords)
    }
    hint = (item.review.source_issue_hint or "").casefold()
    if hint in ISSUE_HINT_TOPICS:
        topics.add(ISSUE_HINT_TOPICS[hint])
    if not topics:
        topics.add(ReviewTopic.NO_CLEAR_ISSUE if item.review.rating >= 3 else ReviewTopic.OTHER)
    return tuple(sorted(topics, key=str))


def _rule_label(item: PreparedReview) -> ModelReviewLabel:
    topics = _rule_topics(item)
    confidence = Decimal("0.82")
    if item.detected_language == "unknown":
        confidence -= Decimal("0.15")
    if item.translation_status == "unavailable" and item.detected_language not in {"en", "zh-CN"}:
        confidence -= Decimal("0.10")
    if QualityFlag.LANGUAGE_MISMATCH in item.quality_flags:
        confidence -= Decimal("0.08")
    return ModelReviewLabel(
        review_id=item.review.review_id,
        sentiment=_sentiment_from_rating(item.review.rating),
        topics=topics,
        confidence=max(confidence, Decimal("0.30")),
    )


def _parse_model_output(
    raw: str | dict[str, object],
    expected_ids: set[str],
) -> dict[str, ModelReviewLabel]:
    try:
        payload: Any = json.loads(raw) if isinstance(raw, str) else raw
        output = ModelBatchOutput.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise ReviewModelError("model returned invalid structured output") from exc

    labels = {label.review_id: label for label in output.labels}
    label_ids = [label.review_id for label in output.labels]
    if len(labels) != len(label_ids):
        raise ReviewModelError("model returned duplicate review_id")
    if set(labels) != expected_ids:
        missing = sorted(expected_ids - set(labels))
        unknown = sorted(set(labels) - expected_ids)
        raise ReviewModelError(
            f"model evidence ids must exactly match input; missing={missing}, unknown={unknown}"
        )
    return labels


async def _model_labels(
    model: ReviewModel,
    included: tuple[PreparedReview, ...],
    config: ReviewAnalysisConfig,
) -> dict[str, ModelReviewLabel]:
    try:
        raw = await asyncio.wait_for(
            model.analyze(included),
            timeout=float(config.model_timeout_seconds),
        )
    except TimeoutError as exc:
        raise ReviewModelError("review model timed out") from exc
    except Exception as exc:
        raise ReviewModelError("review model failed") from exc
    labels = _parse_model_output(raw, {item.review.review_id for item in included})
    below_threshold = sorted(
        review_id
        for review_id, label in labels.items()
        if label.confidence < config.minimum_topic_confidence
    )
    if below_threshold:
        raise ReviewModelError(
            f"model confidence is below the configured threshold for review_ids={below_threshold}"
        )
    return labels


async def _translate_missing(
    prepared: tuple[PreparedReview, ...],
    translator: ReviewTranslator | None,
    config: ReviewAnalysisConfig,
) -> tuple[PreparedReview, ...]:
    if translator is None:
        return prepared
    translated_items: list[PreparedReview] = []
    for item in prepared:
        if (
            not item.included
            or item.translation_status != TranslationStatus.UNAVAILABLE
            or item.detected_language == "unknown"
        ):
            translated_items.append(item)
            continue
        try:
            translated = await asyncio.wait_for(
                translator.translate(
                    item.normalized_content,
                    source_language=item.detected_language,
                    target_language=config.target_language,
                ),
                timeout=float(config.translation_timeout_seconds),
            )
            translated = translated.strip()
            if not translated:
                raise ValueError("translator returned blank text")
        except Exception:
            translated_items.append(
                item.model_copy(
                    update={"translation_status": TranslationStatus.FAILED},
                )
            )
        else:
            translated_items.append(
                item.model_copy(
                    update={
                        "analysis_content": translated[: config.maximum_content_length],
                        "display_translation": translated,
                        "translation_status": TranslationStatus.PROVIDED,
                    }
                )
            )
    return tuple(translated_items)


def _judgement(
    item: PreparedReview,
    label: ModelReviewLabel,
    origin: AnalysisOrigin,
) -> ReviewJudgement:
    translated = item.display_translation
    return ReviewJudgement(
        review_id=item.review.review_id,
        product_id=item.review.product_id,
        site=item.review.site,
        rating=item.review.rating,
        original_content=item.review.content,
        translated_content=translated,
        display_content=translated or item.review.content,
        declared_language=item.review.declared_language,
        detected_language=item.detected_language,
        translation_status=item.translation_status,
        sentiment=label.sentiment,
        topics=label.topics,
        confidence=label.confidence,
        origin=origin,
        source_created_at=item.review.source_created_at,
        quality_flags=item.quality_flags,
    )


def _evidence(item: ReviewJudgement) -> EvidenceReference:
    return EvidenceReference(
        review_id=item.review_id,
        original_content=item.original_content,
        translated_content=item.translated_content,
        language=item.detected_language,
        rating=item.rating,
        source_created_at=item.source_created_at,
        sentiment=item.sentiment,
        confidence=item.confidence,
    )


def _topic_aggregates(
    judgements: tuple[ReviewJudgement, ...],
    config: ReviewAnalysisConfig,
) -> tuple[TopicAggregate, ...]:
    total = Decimal(len(judgements))
    aggregates: list[TopicAggregate] = []
    for topic in ReviewTopic:
        matching = [item for item in judgements if topic in item.topics]
        if not matching:
            continue
        negative = [item for item in matching if item.sentiment == ReviewSentiment.NEGATIVE]
        severity_values = [
            Decimal(5 - item.rating) / FOUR
            for item in matching
            if item.sentiment == ReviewSentiment.NEGATIVE
        ]
        severity = (
            _quantize(sum(severity_values, ZERO) / Decimal(len(severity_values)))
            if severity_values
            else ZERO
        )
        representatives = sorted(
            matching,
            key=lambda item: (
                item.sentiment != ReviewSentiment.NEGATIVE,
                item.rating,
                -item.confidence,
                item.review_id,
            ),
        )[: config.representative_limit]
        aggregates.append(
            TopicAggregate(
                topic=topic,
                count=len(matching),
                frequency_rate=_quantize(Decimal(len(matching)) / total),
                negative_count=len(negative),
                severity=severity,
                evidence=tuple(_evidence(item) for item in representatives),
            )
        )
    aggregates.sort(
        key=lambda item: (
            -item.negative_count,
            -item.count,
            item.topic,
        )
    )
    return tuple(aggregates)


def _pain_points(
    judgements: tuple[ReviewJudgement, ...],
    topics: tuple[TopicAggregate, ...],
    config: ReviewAnalysisConfig,
) -> tuple[PainPointAggregate, ...]:
    total = Decimal(len(judgements))
    pain_points = [
        PainPointAggregate(
            pain_point=topic.topic,
            negative_count=topic.negative_count,
            frequency_rate=_quantize(Decimal(topic.negative_count) / total),
            severity=topic.severity,
            affected_sites=tuple(
                sorted(
                    {
                        judgement.site
                        for judgement in judgements
                        if topic.topic in judgement.topics
                        and judgement.sentiment == ReviewSentiment.NEGATIVE
                    }
                )
            ),
            evidence=tuple(
                evidence
                for evidence in topic.evidence
                if evidence.sentiment == ReviewSentiment.NEGATIVE
            )[: config.representative_limit],
        )
        for topic in topics
        if topic.negative_count > 0
        and topic.topic not in {ReviewTopic.NO_CLEAR_ISSUE}
        and topic.severity > ZERO
    ]
    pain_points.sort(
        key=lambda item: (
            -item.severity,
            -item.negative_count,
            item.pain_point,
        )
    )
    return tuple(pain_points)


def _keywords(
    prepared: tuple[PreparedReview, ...],
    known_review_ids: set[str],
) -> tuple[KeywordAggregate, ...]:
    occurrences: Counter[str] = Counter()
    review_ids: dict[str, set[str]] = defaultdict(set)
    for item in prepared:
        review_id = item.review.review_id
        if review_id not in known_review_ids:
            continue
        text = f"{item.normalized_content} {item.analysis_content}".casefold()
        for keywords in TOPIC_KEYWORDS.values():
            for keyword in keywords:
                count = text.count(keyword.casefold())
                if count:
                    occurrences[keyword] += count
                    review_ids[keyword].add(review_id)
    ranked = sorted(
        occurrences,
        key=lambda keyword: (
            -len(review_ids[keyword]),
            -occurrences[keyword],
            keyword,
        ),
    )[:20]
    return tuple(
        KeywordAggregate(
            keyword=keyword,
            count=occurrences[keyword],
            review_count=len(review_ids[keyword]),
            review_ids=tuple(sorted(review_ids[keyword])),
        )
        for keyword in ranked
    )


def _trends(judgements: tuple[ReviewJudgement, ...]) -> tuple[TrendPoint, ...]:
    groups: dict[tuple[str, str], list[ReviewJudgement]] = defaultdict(list)
    for item in judgements:
        groups[(item.site, item.source_created_at.strftime("%Y-%m"))].append(item)
    points: list[TrendPoint] = []
    for (site, month), items in sorted(groups.items()):
        topic_counts: Counter[ReviewTopic] = Counter()
        for item in items:
            topic_counts.update(item.topics)
        points.append(
            TrendPoint(
                site=site,
                month=month,
                review_count=len(items),
                negative_count=sum(item.sentiment == ReviewSentiment.NEGATIVE for item in items),
                average_rating=_quantize(
                    Decimal(sum(item.rating for item in items)) / Decimal(len(items))
                ),
                topic_counts=dict(sorted(topic_counts.items(), key=lambda pair: pair[0])),
            )
        )
    return tuple(points)


def _quality(prepared: tuple[PreparedReview, ...]) -> QualityReport:
    flag_counts = Counter(flag for item in prepared for flag in item.quality_flags)
    excluded = tuple(item.review.review_id for item in prepared if not item.included)
    return QualityReport(
        received_count=len(prepared),
        included_count=len(prepared) - len(excluded),
        excluded_count=len(excluded),
        flag_counts=dict(sorted(flag_counts.items(), key=lambda pair: pair[0])),
        excluded_review_ids=excluded,
    )


async def analyze_reviews(
    reviews: Iterable[ReviewInput],
    *,
    model: ReviewModel | None = None,
    translator: ReviewTranslator | None = None,
    config: ReviewAnalysisConfig = DEFAULT_REVIEW_ANALYSIS_CONFIG,
) -> ReviewAnalysisReport:
    review_list = list(reviews)
    if not review_list:
        raise ReviewAnalysisError("at least one review is required")
    products = {review.product_id for review in review_list}
    sources = {review.source.model_dump_json() for review in review_list}
    if len(sources) != 1:
        raise ReviewAnalysisError("all reviews must use the same source metadata")

    prepared = await _translate_missing(
        prepare_reviews(review_list, config),
        translator,
        config,
    )
    included = tuple(item for item in prepared if item.included)
    if not included:
        raise ReviewAnalysisError("no analyzable reviews remain after quality checks")

    if model is None:
        labels = {item.review.review_id: _rule_label(item) for item in included}
        origin = AnalysisOrigin.RULE
    else:
        labels = await _model_labels(model, included, config)
        origin = AnalysisOrigin.MODEL

    judgements = tuple(
        _judgement(item, labels[item.review.review_id], origin)
        for item in sorted(included, key=lambda row: row.review.review_id)
    )
    sentiment_counts = Counter(item.sentiment for item in judgements)
    topics = _topic_aggregates(judgements, config)
    source = review_list[0].source
    return ReviewAnalysisReport(
        analyzer_version=config.version,
        product_ids=tuple(sorted(products)),
        source=source,
        is_mock_data=source.is_mock,
        quality=_quality(prepared),
        sentiment=SentimentAggregate(
            positive=sentiment_counts[ReviewSentiment.POSITIVE],
            neutral=sentiment_counts[ReviewSentiment.NEUTRAL],
            negative=sentiment_counts[ReviewSentiment.NEGATIVE],
        ),
        topics=topics,
        pain_points=_pain_points(judgements, topics, config),
        keywords=_keywords(prepared, {item.review_id for item in judgements}),
        trends=_trends(judgements),
        judgements=judgements,
        facts=(
            f"received {len(review_list)} reviews",
            f"included {len(judgements)} reviews after deterministic quality checks",
            f"analysis origin is {origin.value}",
        ),
    )
