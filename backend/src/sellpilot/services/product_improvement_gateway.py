import json
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from sellpilot.core.config import Settings
from sellpilot.services.model_gateway import ModelGatewayError


class GeneratedImprovement(BaseModel):
    category: str
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=4000)


class GeneratedImprovementList(BaseModel):
    suggestions: list[GeneratedImprovement]


class ProductImprovementGateway:
    """Generate wording only for evidence-backed categories supplied by the service."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if settings.content_model_provider != "aliyun_bailian":
            raise ValueError("Product improvement gateway requires aliyun_bailian mode")
        assert settings.bailian_api_key is not None
        assert settings.bailian_base_url is not None
        self.model_name = settings.bailian_model
        self._api_key = settings.bailian_api_key.get_secret_value()
        self._base_url = settings.bailian_base_url.rstrip("/")
        self._timeout = settings.bailian_timeout_seconds
        self._transport = transport

    async def generate(self, product_id: str, evidence_groups: list[dict]) -> dict[str, Any]:
        allowed_categories = [group["category"] for group in evidence_groups]
        prompt = {
            "task": (
                "根据评论中的明确缺点，为每个输入类别生成一条中文产品改良建议。"
                "只能使用 evidence_groups 中已有的 category，不得新增、推断或替换类别；"
                "不得把正向陈述改写成问题。标题要具体，方案要可执行，并明确需要人工核对。"
            ),
            "product_id": product_id,
            "allowed_categories": allowed_categories,
            "evidence_groups": evidence_groups,
            "output_schema": GeneratedImprovementList.model_json_schema(),
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是电商产品改良助手。仅依据提供的评论证据输出 JSON，"
                        "不能创造证据中不存在的问题。"
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            result = GeneratedImprovementList.model_validate(json.loads(content))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise ModelGatewayError(
                "Product improvement model request or response was invalid"
            ) from None
        except ValidationError:
            raise ModelGatewayError(
                "Product improvement model output failed schema validation"
            ) from None

        generated = {item.category: item for item in result.suggestions}
        if set(generated) != set(allowed_categories) or len(result.suggestions) != len(
            allowed_categories
        ):
            raise ModelGatewayError(
                "Product improvement model changed the evidence-backed categories"
            )
        return generated
