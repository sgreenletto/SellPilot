from sellpilot.services.commerce_normalization import (
    extract_category_external_id,
    extract_requested_category_text,
)


def test_selection_category_aliases_map_to_stable_codes() -> None:
    for alias in ("婴儿产品", "母婴", "婴儿用品", "baby products"):
        assert extract_category_external_id(f"分析新加坡站{alias}的选品机会") == "CAT008"


def test_selection_category_request_distinguishes_missing_and_unknown() -> None:
    assert extract_requested_category_text("分析新加坡站的选品机会") is None
    assert (
        extract_requested_category_text("分析新加坡站航空发动机产品的选品机会") == "航空发动机产品"
    )
