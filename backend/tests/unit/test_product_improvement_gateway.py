import json

import httpx
import pytest

from sellpilot.core.config import Settings
from sellpilot.services.model_gateway import ModelGatewayError
from sellpilot.services.product_improvement_gateway import ProductImprovementGateway


def settings() -> Settings:
    return Settings(
        CONTENT_MODEL_PROVIDER="aliyun_bailian",
        DASHSCOPE_API_KEY="test-key",
        BAILIAN_BASE_URL="https://example.invalid/v1",
        BAILIAN_MODEL="qwen-plus",
    )


@pytest.mark.asyncio
async def test_generates_only_supplied_evidence_category() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "suggestions": [
                                        {
                                            "category": "product_quality",
                                            "title": "改善表面做工",
                                            "description": "复核表面处理标准并进行样品验收。",
                                        }
                                    ]
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    gateway = ProductImprovementGateway(settings(), transport=httpx.MockTransport(handler))
    result = await gateway.generate(
        "PROD0001",
        [
            {
                "category": "product_quality",
                "reviews": [{"review_id": "REV1", "original": "finish is basic"}],
            }
        ],
    )
    assert result["product_quality"].title == "改善表面做工"


@pytest.mark.asyncio
async def test_rejects_model_invented_description_mismatch() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "suggestions": [
                                        {
                                            "category": "description_mismatch",
                                            "title": "修改描述",
                                            "description": "修改商品描述。",
                                        }
                                    ]
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    gateway = ProductImprovementGateway(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(ModelGatewayError, match="changed the evidence-backed categories"):
        await gateway.generate(
            "PROD0001",
            [
                {
                    "category": "product_quality",
                    "reviews": [{"review_id": "REV1", "original": "finish is basic"}],
                }
            ],
        )
