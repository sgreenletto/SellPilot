"""LLM 调用服务 —— OpenAI 兼容接口。"""

import logging
from typing import Any

import httpx

from sellpilot.core.config import Settings
from sellpilot.core.exceptions import ModelCallFailureError

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport

    async def chat(
        self, messages: list[dict[str, str]], *, temperature: float = 0.3, max_tokens: int = 1024
    ) -> str:
        model = self._settings.llm_model or "qwen-plus"
        endpoint = f"{self._settings.llm_base_url.rstrip('/')}/chat/completions"
        try:
            async with httpx.AsyncClient(
                timeout=30,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "Authorization": (
                            f"Bearer {self._settings.llm_api_key.get_secret_value()}"
                        ),
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                response.raise_for_status()
                body: dict[str, Any] = response.json()
            content = str(body["choices"][0]["message"]["content"] or "")
            usage = body.get("usage")
        except httpx.TimeoutException:
            raise ModelCallFailureError("Model provider request timed out") from None
        except httpx.HTTPStatusError as exc:
            raise ModelCallFailureError(
                f"Model provider returned HTTP {exc.response.status_code}"
            ) from None
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            raise ModelCallFailureError("Model provider request or response was invalid") from None

        logger.info(
            "LLM response: model=%s tokens=%d",
            model,
            int(usage.get("total_tokens") or 0) if isinstance(usage, dict) else 0,
        )
        return content
