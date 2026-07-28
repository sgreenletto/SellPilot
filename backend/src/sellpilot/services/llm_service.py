"""LLM 调用服务 —— OpenAI 兼容接口。"""

import logging
from typing import Any

from sellpilot.core.config import Settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            from openai import OpenAI

            api_key = self._settings.llm_api_key.get_secret_value()
            self._client = OpenAI(
                api_key=api_key or "sk-placeholder",
                base_url=self._settings.llm_base_url,
            )
            logger.info(
                "LLM ready: model=%s base_url=%s",
                self._settings.llm_model,
                self._settings.llm_base_url,
            )
        return self._client

    def chat(
        self, messages: list[dict[str, str]], *, temperature: float = 0.3, max_tokens: int = 1024
    ) -> str:
        model = self._settings.llm_model or "qwen-plus"
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        logger.info(
            "LLM response: model=%s tokens=%d",
            model,
            response.usage.total_tokens if response.usage else 0,
        )
        return content
