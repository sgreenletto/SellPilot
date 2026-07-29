import pytest

from sellpilot.domain.content_generation.models import ListingFacts, LocalizedListing
from sellpilot.domain.content_generation.workflow import (
    check_listing,
    generate_with_quality_loop,
)
from sellpilot.services.model_gateway import OfflineTemplateGateway


def _facts() -> ListingFacts:
    return ListingFacts(
        product_id="PROD0001",
        title="Travel Bottle",
        description="Reusable bottle",
        category_name="Outdoor",
        site="sg",
        target_language="en",
        specifications={"capacity": "750 ml"},
    )


def _listing(*, description: str, include_fact: bool = False) -> LocalizedListing:
    return LocalizedListing(
        title="Travel Bottle",
        bullet_points=[
            "Reusable",
            "Lightweight",
            "750 ml capacity" if include_fact else "Suitable for travel",
        ],
        description=description,
        marketing_copy="Outdoor bottle for everyday travel",
        keywords=["bottle", "outdoor"],
        target_language="en",
        generation_mode="test",
    )


def test_quality_check_rejects_forbidden_claim_and_missing_fact() -> None:
    result = check_listing(_listing(description="The best ever bottle"), _facts(), attempts=1)

    assert result.passed is False
    assert result.fact_issues == ["missing protected fact: 750 ml"]
    assert result.compliance_issues == ["forbidden claim: best ever"]


def test_quality_check_uses_requested_keywords_and_requires_every_sku() -> None:
    facts = _facts().model_copy(
        update={
            "requested_keywords": ["travel", "leakproof"],
            "sku_facts": [{"seller_sku": "BOTTLE-BLUE"}],
        }
    )

    result = check_listing(
        _listing(description="Verified capacity: 750 ml for travel", include_fact=True),
        facts,
        attempts=1,
    )

    assert result.keyword_coverage == 0.5
    assert result.completeness_issues == ["missing SKU content: BOTTLE-BLUE"]
    assert "missing requested keyword: leakproof" in result.seo_issues


def test_quality_check_accepts_localized_n_in_one_fact() -> None:
    facts = _facts().model_copy(update={"specifications": {"Ports": "6-in-1"}})
    listing = _listing(description="这是一款便携的 6合1 扩展坞", include_fact=False)

    result = check_listing(listing, facts, attempts=1)

    assert result.fact_issues == []


def test_quality_check_rejects_unsupported_faq_and_sku_technical_claims() -> None:
    listing = LocalizedListing(
        title="USB-C Hub",
        bullet_points=["便携设计", "适合办公", "6合1接口"],
        description="Multi-port hub for laptop and tablet workflows, 6合1版本",
        marketing_copy="满足日常连接需求",
        faq=[
            {
                "question": "是否支持4K？",
                "answer": "最高输出1080p@60Hz，所有接口实测可同时稳定工作。",
            }
        ],
        sku_content=[
            {
                "sku": "HUB-01",
                "description": "含2×USB-A 3.0、1×HDMI和PD充电接口",
            }
        ],
        keywords=["hub"],
        target_language="zh-CN",
        generation_mode="test",
    )
    facts = _facts().model_copy(
        update={
            "title": "USB-C Hub",
            "description": "Multi-port hub for laptop and tablet workflows",
            "specifications": {"Ports": "6-in-1"},
            "target_language": "zh-CN",
        }
    )

    result = check_listing(listing, facts, attempts=1)

    assert "unsupported claim: 实测" in result.fact_issues
    assert "unsupported claim: 同时稳定" in result.fact_issues
    assert "unsupported technical fact: 4k" in result.fact_issues
    assert "unsupported technical fact: hdmi" in result.fact_issues


def test_quality_check_enforces_mock_site_seo_and_localization_rules() -> None:
    listing = LocalizedListing(
        title=f"Travel Bottle {'x' * 120}",
        bullet_points=["Reusable", "Lightweight", "750 ml capacity"],
        description="travel travel travel travel travel travel",
        marketing_copy="Outdoor bottle",
        keywords=["travel", "Travel"],
        target_language="zh-CN",
        generation_mode="test",
    )
    facts = _facts().model_copy(
        update={"target_language": "zh-CN", "requested_keywords": ["travel"]}
    )

    result = check_listing(listing, facts, attempts=1)

    assert "title exceeds site limit: 120" in result.compliance_issues
    assert "duplicate generated keywords" in result.seo_issues
    assert "keyword stuffing: travel" in result.seo_issues
    assert "content is not localized to Chinese" in result.localization_issues
    assert "keyword not localized: travel" in result.localization_issues


def test_quality_check_requires_target_market_keyword_in_title() -> None:
    facts = _facts().model_copy(update={"requested_keywords": ["leakproof"]})
    listing = _listing(
        description="Verified 750 ml leakproof travel bottle",
        include_fact=True,
    ).model_copy(update={"keywords": ["outdoor"]})

    result = check_listing(listing, facts, attempts=1)

    assert result.keyword_coverage == 1
    assert result.seo_issues == ["title does not contain a target-market keyword"]


def test_cross_language_keyword_uses_chinese_intent_and_market_translation() -> None:
    facts = _facts().model_copy(update={"requested_keywords": ["旅行水杯"]})
    listing = _listing(
        description="Verified 750 ml travel bottle",
        include_fact=True,
    ).model_copy(
        update={
            "title": "Travel Bottle for Outdoor Use",
            "keywords": ["travel bottle", "outdoor bottle"],
            "keyword_suggestions_zh": ["旅行水杯", "户外水杯"],
        }
    )

    result = check_listing(listing, facts, attempts=1)

    assert result.keyword_coverage == 1
    assert result.seo_issues == []


def test_quality_check_rejects_unsupported_factual_keyword_without_duplicate_noise() -> None:
    facts = _facts().model_copy(update={"requested_keywords": ["容量大"]})
    listing = _listing(description="Verified capacity: 750 ml", include_fact=True)

    result = check_listing(listing, facts, attempts=1)

    assert result.keyword_coverage == 1
    assert result.seo_issues == ["unsupported factual keyword: 容量大"]


def test_quality_check_requires_generated_keywords_to_follow_target_language() -> None:
    facts = _facts().model_copy(update={"target_language": "zh-CN"})
    listing = _listing(description="已核验容量为 750 ml", include_fact=True).model_copy(
        update={
            "bullet_points": ["适合日常使用", "轻巧便携", "容量为 750 ml"],
            "marketing_copy": "适合户外出行",
            "keywords": ["USB-C", "affordable hub", "便携扩展"],
            "target_language": "zh-CN",
        }
    )

    result = check_listing(listing, facts, attempts=1)

    assert result.localization_issues == ["keyword not localized: affordable hub"]


def test_operator_keyword_suggestions_do_not_block_publishable_content() -> None:
    listing = _listing(description="Verified capacity: 750 ml", include_fact=True).model_copy(
        update={
            "keyword_suggestions_zh": ["便携水杯", "affordable bottle", "USB-C"],
        }
    )

    result = check_listing(listing, _facts(), attempts=1)

    assert result.localization_issues == []


@pytest.mark.asyncio
async def test_quality_loop_retries_with_structured_issues() -> None:
    class Gateway:
        provider = "test"
        model_name = "test"
        generation_mode = "test"

        def __init__(self) -> None:
            self.received: list[list[str]] = []

        async def generate(self, facts, issues=None):
            self.received.append(list(issues or []))
            if len(self.received) == 1:
                return _listing(description="Generic copy")
            return _listing(description="Verified capacity: 750 ml", include_fact=True)

    gateway = Gateway()
    result = await generate_with_quality_loop(gateway, _facts())

    assert result.quality.passed is True
    assert result.quality.attempts == 2
    assert gateway.received[1] == ["missing protected fact: 750 ml"]


@pytest.mark.asyncio
async def test_quality_loop_does_not_retry_an_unsupported_user_keyword() -> None:
    class Gateway:
        provider = "test"
        model_name = "test"
        generation_mode = "test"

        def __init__(self) -> None:
            self.calls = 0

        async def generate(self, facts, issues=None):
            self.calls += 1
            return _listing(description="Verified capacity: 750 ml", include_fact=True)

    gateway = Gateway()
    facts = _facts().model_copy(update={"requested_keywords": ["容量大"]})
    result = await generate_with_quality_loop(gateway, facts)

    assert gateway.calls == 1
    assert result.quality.seo_issues == ["unsupported factual keyword: 容量大"]


@pytest.mark.asyncio
async def test_offline_gateway_localizes_template_without_claiming_real_llm() -> None:
    facts = _facts().model_copy(
        update={
            "target_language": "zh-CN",
            "sku_facts": [{"external_id": "variant-1", "seller_sku": "BOTTLE-BLUE"}],
        }
    )

    result = await OfflineTemplateGateway().generate(facts)

    assert result.generation_mode == "offline_template"
    assert result.bullet_points[0] == "商品：Travel Bottle"
    assert "规格信息" in result.bullet_points[2]
    assert "适合：general" in result.bullet_points
    assert "商品原始描述" in result.description
    assert result.faq[0].question == "商品包含哪些规格信息？"
    assert result.sku_content[0].sku == "BOTTLE-BLUE"
    assert all(
        any("\u3400" <= char <= "\u9fff" for char in item) for item in result.keyword_suggestions_zh
    )
