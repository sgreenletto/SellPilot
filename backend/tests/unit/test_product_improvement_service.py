from types import SimpleNamespace

from sellpilot.services.product_improvement import ProductImprovementService


def evidence(label: str, original: str, translated: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        label=label,
        excerpt=original,
        translated_excerpt=translated,
    )


def test_normal_delivery_expression_is_not_an_improvement_topic() -> None:
    item = evidence(
        "logistics",
        "Acceptable for the price; delivery took the usual time.",
        "以这个价格来说可以接受，配送时效也属正常。",
    )

    assert ProductImprovementService._effective_topic(item) is None


def test_explicit_delivery_delay_remains_an_improvement_topic() -> None:
    item = evidence(
        "logistics",
        "Delivery was delayed for several days.",
        "配送延迟了好几天。",
    )

    assert ProductImprovementService._effective_topic(item) == "logistics"
