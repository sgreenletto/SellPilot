import re
import unicodedata
from collections.abc import Iterable

from sellpilot.domain.review_analysis.models import (
    PreparedReview,
    QualityFlag,
    ReviewAnalysisConfig,
    ReviewInput,
    TranslationStatus,
)

LANGUAGE_ALIASES = {
    "english": "en",
    "en": "en",
    "filipino": "tl",
    "tagalog": "tl",
    "tl": "tl",
    "indonesian": "id",
    "id": "id",
    "malay": "ms",
    "ms": "ms",
    "thai": "th",
    "th": "th",
    "vietnamese": "vi",
    "vi": "vi",
    "chinese": "zh-CN",
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
}

LANGUAGE_MARKERS = {
    "en": {"the", "and", "good", "item", "delivery", "quality", "but", "size"},
    "tl": {"ang", "pero", "maayos", "mabilis", "sobra", "huli", "item"},
    "id": {"dan", "barang", "produk", "pengiriman", "sesuai", "tidak", "bagus"},
    "ms": {"dan", "barang", "produk", "penghantaran", "berbaloi", "tidak", "baik"},
    "vi": {"và", "hàng", "sản", "phẩm", "giao", "không", "tốt", "nhưng"},
}

SPAM_PATTERN = re.compile(
    r"(https?://|www\.|(.)\2{12,}|\b(?:buy now|click here|free money)\b)",
    re.IGNORECASE,
)
WORD_PATTERN = re.compile(r"[^\W\d_]+", re.UNICODE)
SPACE_PATTERN = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    return SPACE_PATTERN.sub(" ", unicodedata.normalize("NFKC", value)).strip()


def _is_emoji_only(value: str) -> bool:
    meaningful = [
        char
        for char in value
        if not char.isspace() and not unicodedata.category(char).startswith(("P", "S", "M"))
    ]
    return not meaningful and bool(value.strip())


def detect_language(value: str) -> str:
    if re.search(r"[\u0E00-\u0E7F]", value):
        return "th"
    if re.search(r"[\u4E00-\u9FFF]", value):
        return "zh-CN"
    lowered_words = {word.casefold() for word in WORD_PATTERN.findall(value)}
    if not lowered_words:
        return "unknown"
    scores = {
        language: len(lowered_words & markers) for language, markers in LANGUAGE_MARKERS.items()
    }
    best_language, best_score = max(scores.items(), key=lambda item: (item[1], item[0]))
    if best_score == 0:
        return "unknown"
    if best_language in {"id", "ms"} and scores["id"] == scores["ms"]:
        if {"pengiriman", "sesuai", "bagus"} & lowered_words:
            return "id"
        if {"penghantaran", "berbaloi", "baik"} & lowered_words:
            return "ms"
    return best_language


def _declared_language(value: str | None) -> str | None:
    if value is None:
        return None
    return LANGUAGE_ALIASES.get(value.casefold(), value)


def prepare_reviews(
    reviews: Iterable[ReviewInput],
    config: ReviewAnalysisConfig,
) -> tuple[PreparedReview, ...]:
    review_list = list(reviews)
    ids = [review.review_id for review in review_list]
    if len(ids) != len(set(ids)):
        raise ValueError("review_id must be unique within one analysis batch")

    seen_content: dict[tuple[str, str], str] = {}
    prepared: list[PreparedReview] = []
    for review in review_list:
        normalized = normalize_text(review.content)
        flags: list[QualityFlag] = []
        if not normalized:
            flags.append(QualityFlag.EMPTY)
        elif _is_emoji_only(normalized):
            flags.append(QualityFlag.EMOJI_ONLY)
        if SPAM_PATTERN.search(normalized):
            flags.append(QualityFlag.SPAM)

        truncated = normalized[: config.maximum_content_length]
        if len(normalized) > config.maximum_content_length:
            flags.append(QualityFlag.TRUNCATED)

        detected = detect_language(truncated)
        declared = _declared_language(review.declared_language)
        if detected == "unknown":
            flags.append(QualityFlag.UNKNOWN_LANGUAGE)
        elif declared is not None and declared != detected:
            flags.append(QualityFlag.LANGUAGE_MISMATCH)

        duplicate_key = (review.product_id, truncated.casefold())
        duplicate_of = seen_content.get(duplicate_key) if truncated else None
        if duplicate_of is not None:
            flags.append(QualityFlag.DUPLICATE)
        elif truncated:
            seen_content[duplicate_key] = review.review_id

        translated = normalize_text(review.translated_content or "")
        if detected == config.target_language:
            translation_status = TranslationStatus.NOT_NEEDED
            analysis_content = truncated
        elif translated:
            translation_status = TranslationStatus.PROVIDED
            analysis_content = translated[: config.maximum_content_length]
        else:
            translation_status = TranslationStatus.UNAVAILABLE
            analysis_content = truncated

        excluded_flags = {
            QualityFlag.EMPTY,
            QualityFlag.EMOJI_ONLY,
            QualityFlag.SPAM,
            QualityFlag.DUPLICATE,
        }
        prepared.append(
            PreparedReview(
                review=review,
                normalized_content=truncated,
                analysis_content=analysis_content,
                display_translation=translated or None,
                detected_language=detected,
                translation_status=translation_status,
                quality_flags=tuple(sorted(set(flags), key=str)),
                included=not bool(set(flags) & excluded_flags),
                duplicate_of=duplicate_of,
            )
        )
    return tuple(prepared)
