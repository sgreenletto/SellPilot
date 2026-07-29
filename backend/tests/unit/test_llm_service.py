import httpx
import pytest

from sellpilot.core.config import Settings
from sellpilot.core.exceptions import ModelCallFailureError
from sellpilot.services.llm_service import LLMService


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        LLM_API_KEY="synthetic-test-key",
        LLM_BASE_URL="https://example.test/compatible-mode/v1",
        LLM_MODEL="test-model",
    )


async def test_llm_service_uses_openai_compatible_http_contract():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://example.test/compatible-mode/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer synthetic-test-key"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "grounded answer"}}],
                "usage": {"total_tokens": 7},
            },
        )

    result = await LLMService(
        _settings(),
        transport=httpx.MockTransport(handler),
    ).chat([{"role": "user", "content": "synthetic question"}])

    assert result == "grounded answer"


@pytest.mark.parametrize("status_code", [401, 403, 404, 429, 500])
async def test_llm_service_preserves_safe_upstream_http_status(status_code: int):
    service = LLMService(
        _settings(),
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(status_code, json={"secret": "must-not-leak"})
        ),
    )

    with pytest.raises(
        ModelCallFailureError,
        match=f"Model provider returned HTTP {status_code}",
    ):
        await service.chat([{"role": "user", "content": "synthetic question"}])


async def test_llm_service_reports_timeout_without_provider_payload():
    def timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("token=must-not-leak")

    service = LLMService(_settings(), transport=httpx.MockTransport(timeout))

    with pytest.raises(ModelCallFailureError, match="Model provider request timed out"):
        await service.chat([{"role": "user", "content": "synthetic question"}])
