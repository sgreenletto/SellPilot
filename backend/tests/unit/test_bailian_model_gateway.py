import json

import httpx
import pytest
from pydantic import ValidationError

from sellpilot.core.config import Settings
from sellpilot.domain.content_generation.models import ListingFacts
from sellpilot.services.model_gateway import (
    BailianModelGateway,
    ModelGatewayError,
    OfflineTemplateGateway,
    build_model_gateway,
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


@pytest.mark.asyncio
async def test_bailian_gateway_uses_structured_output_and_records_usage() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-only-key"
        payload = json.loads(request.content)
        assert payload["response_format"] == {"type": "json_object"}
        assert "JSON" in payload["messages"][0]["content"]
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
