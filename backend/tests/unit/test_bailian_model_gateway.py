import json
from inspect import signature

import httpx
import pytest
from pydantic import ValidationError

from sellpilot.core.config import Settings
from sellpilot.domain.content_generation.models import ListingFacts
from sellpilot.services.model_gateway import (
    BailianModelGateway,
    ModelGatewayError,
    OfflineTemplateGateway,
    _operator_keyword_suggestions,
    build_model_gateway,
    build_selection_explanation_generator,
    translate_review_batch,
)


def bailian_settings() -> Settings:
    return Settings(
        _env_file=None,
        CONTENT_MODEL_PROVIDER="aliyun_bailian",
        DASHSCOPE_API_KEY="test-only-key",
        BAILIAN_BASE_URL="https://example.test/compatible-mode/v1",
        BAILIAN_MODEL="qwen-plus",
    )


def facts() -> ListingFacts:
    return ListingFacts(
        product_id="PROD0001",
        title="USB-C Hub",
        description="A compact multi-port hub.",
        category_name="Consumer Electronics",
        site="SG",
        target_language="en",
        audience="general",
        selling_points=["compact"],
        requested_keywords=["USB-C"],
        specifications={"Ports": "4"},
        sku_facts=[{"seller_sku": "SKU-1", "name": "Black"}],
    )


def valid_listing() -> dict[str, object]:
    return {
        "title": "USB-C Hub",
        "bullet_points": ["USB-C", "Ports: 4", "Compact design"],
        "description": "A compact multi-port hub with Ports: 4.",
        "marketing_copy": "USB-C hub for everyday use.",
        "faq": [{"question": "How many ports?", "answer": "Ports: 4."}],
        "sku_content": [{"sku": "SKU-1", "description": "Black"}],
        "keywords": ["USB-C"],
        "keyword_suggestions_zh": [
            "laptop hub",
            "tablet hub",
            "affordable hub",
            "multi-port adapter",
            "USB-C adapter",
            "compact hub",
            "productivity hub",
            "budget hub",
        ],
        "target_language": "en",
        "generation_mode": "ignored-by-server",
    }


def test_bailian_requires_explicit_credentials() -> None:
    with pytest.raises(ValidationError, match="DASHSCOPE_API_KEY"):
        Settings(
            _env_file=None,
            CONTENT_MODEL_PROVIDER="aliyun_bailian",
        )


def test_default_gateway_remains_offline() -> None:
    gateway = build_model_gateway(Settings(_env_file=None))
    assert isinstance(gateway, OfflineTemplateGateway)


def test_review_translation_defaults_to_simplified_chinese() -> None:
    assert signature(translate_review_batch).parameters["target_language"].default == "zh-CN"


def test_operator_suggestions_exclude_unsupported_factual_keyword() -> None:
    product_facts = facts().model_copy(update={"requested_keywords": ["容量大"]})

    result = _operator_keyword_suggestions(
        ["容量大", "便携扩展坞", "laptop hub"],
        product_facts,
    )

    assert "容量大" not in result
    assert result == ["便携扩展坞", "笔记本扩展坞"]


@pytest.mark.asyncio
async def test_bailian_gateway_uses_structured_output_and_records_usage() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-only-key"
        payload = json.loads(request.content)
        assert payload["response_format"] == {"type": "json_object"}
        assert "JSON" in payload["messages"][0]["content"]
        prompt = json.loads(payload["messages"][1]["content"])
        assert prompt["creative_direction"]["target_language"] == "en"
        assert "120 characters" in prompt["task"]
        assert "never repeat a keyword more than five times" in prompt["task"]
        assert "keywords in target_language" in prompt["task"]
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(valid_listing())}}],
                "usage": {
                    "prompt_tokens": 120,
                    "completion_tokens": 80,
                    "total_tokens": 200,
                },
            },
        )

    gateway = BailianModelGateway(
        bailian_settings(),
        transport=httpx.MockTransport(handler),
    )
    result = await gateway.generate(facts())

    assert result.generation_mode == "aliyun_bailian"
    assert result.keyword_suggestions_zh == [
        "笔记本扩展坞",
        "平板扩展坞",
        "实惠扩展坞",
        "多接口转接器",
        "USB-C转接器",
        "便携扩展坞",
        "办公扩展坞",
        "经济型扩展坞",
    ]
    assert gateway.prompt_tokens == 120
    assert gateway.completion_tokens == 80
    assert gateway.total_tokens == 200


@pytest.mark.asyncio
async def test_bailian_gateway_rejects_invalid_schema() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"title": "incomplete"}'}}]},
        )

    gateway = BailianModelGateway(
        bailian_settings(),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ModelGatewayError, match="schema"):
        await gateway.generate(facts())


@pytest.mark.asyncio
async def test_selection_explanation_provenance_is_owned_by_application() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert (
            "Set generation_mode to validated_generator exactly"
            in payload["messages"][0]["content"]
        )
        explanation = {
            "summary": "该商品利润空间稳定。",
            "evidence": {"total_score": "model-controlled-value"},
            "risks": "物流风险数据缺失",
            "generation_mode": "deterministic",
        }
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(explanation)}}]},
        )

    generator = build_selection_explanation_generator(
        bailian_settings(),
        transport=httpx.MockTransport(handler),
    )
    assert generator is not None

    result = await generator(
        {
            "total_score": "72.7",
            "profit": {"profit": "10.79", "margin": "0.4104"},
            "data_completeness": "0.571",
            "recommendation_facts": ["商品机会总分 72.7"],
            "risk_warnings": ["物流风险数据缺失"],
        }
    )

    assert result["generation_mode"] == "validated_generator"
    assert result["risks"] == ["物流风险数据缺失"]
    assert {item["metric"]: item["value"] for item in result["evidence"]} == {
        "total_score": "72.7",
        "profit": "10.79",
        "margin": "0.4104",
        "data_completeness": "0.571",
    }
