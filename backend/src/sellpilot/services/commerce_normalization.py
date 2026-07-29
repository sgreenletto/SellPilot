"""Stable normalization for user-facing commerce identifiers and filters."""

from __future__ import annotations

import re

CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "CAT001": ("消费电子", "电子产品", "consumer electronics"),
    "CAT002": ("家居生活", "家居用品", "home & living", "home living"),
    "CAT003": ("美妆个护", "美容个护", "beauty & personal care", "beauty"),
    "CAT004": ("时尚配饰", "fashion accessories"),
    "CAT005": ("运动户外", "sports & outdoors", "sports"),
    "CAT006": ("宠物用品", "pet supplies"),
    "CAT007": ("厨房电器", "kitchen appliances"),
    "CAT008": (
        "婴儿产品",
        "母婴",
        "婴儿用品",
        "宝宝用品",
        "baby products",
        "baby product",
    ),
}


def normalize_product_external_id(value: str) -> str:
    """Map display aliases such as PROD-001 to the stable Mock ID PROD0001."""

    normalized = value.strip().upper()
    match = re.fullmatch(r"PROD(?:UCT)?[-_ ]*0*(\d{1,4})", normalized)
    if match is None:
        return normalized
    return f"PROD{int(match.group(1)):04d}"


def extract_category_external_id(message: str) -> str | None:
    lowered = message.casefold()
    explicit = re.search(r"\bCAT\d{3}\b", message, flags=re.IGNORECASE)
    if explicit:
        return explicit.group(0).upper()
    for category_id, aliases in CATEGORY_ALIASES.items():
        if any(alias.casefold() in lowered for alias in aliases):
            return category_id
    return None
