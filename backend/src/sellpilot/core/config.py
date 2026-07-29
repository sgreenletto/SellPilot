from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[3]
REPOSITORY_ROOT = BACKEND_ROOT.parent
EXAMPLE_JWT_SECRETS = {
    "change-me",
    "change-me-in-local-env-only",
    "replace_me",
    "replace-me",
    "replace_with_at_least_32_random_characters",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables and the repository .env."""

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="SellPilot", validation_alias="APP_NAME")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    app_env: Literal["development", "test", "production"] = Field(
        default="development", validation_alias="APP_ENV"
    )
    debug: bool = Field(default=False, validation_alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")
    database_url: str = Field(
        default="postgresql+asyncpg://sellpilot:replace_me@localhost:5432/sellpilot",
        validation_alias="DATABASE_URL",
    )
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("change-me-in-local-env-only"),
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        le=1440,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    platform_adapter: Literal["mock", "real"] = Field(
        default="mock", validation_alias="PLATFORM_ADAPTER"
    )
    cors_origins: list[str] = Field(default_factory=list, validation_alias="CORS_ORIGINS")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", validation_alias="LOG_LEVEL"
    )
    file_max_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1,
        le=100 * 1024 * 1024,
        validation_alias="FILE_MAX_SIZE_BYTES",
    )
    tool_default_timeout_seconds: float = Field(
        default=30,
        gt=0,
        le=120,
        validation_alias="TOOL_DEFAULT_TIMEOUT_SECONDS",
    )
    tool_max_timeout_seconds: float = Field(
        default=120,
        gt=0,
        le=600,
        validation_alias="TOOL_MAX_TIMEOUT_SECONDS",
    )
    tool_read_max_attempts: int = Field(
        default=2,
        ge=1,
        le=3,
        validation_alias="TOOL_READ_MAX_ATTEMPTS",
    )
    tool_retry_initial_delay_ms: int = Field(
        default=100,
        ge=0,
        le=60_000,
        validation_alias="TOOL_RETRY_INITIAL_DELAY_MS",
    )
    tool_retry_max_delay_ms: int = Field(
        default=1000,
        ge=0,
        le=60_000,
        validation_alias="TOOL_RETRY_MAX_DELAY_MS",
    )
    tool_audit_payload_max_bytes: int = Field(
        default=16_384,
        ge=1024,
        le=1_048_576,
        validation_alias="TOOL_AUDIT_PAYLOAD_MAX_BYTES",
    )
    task_max_steps: int = Field(
        default=50,
        ge=1,
        le=200,
        validation_alias="TASK_MAX_STEPS",
    )
    task_default_node_timeout_seconds: float = Field(
        default=60,
        gt=0,
        le=300,
        validation_alias="TASK_DEFAULT_NODE_TIMEOUT_SECONDS",
    )
    task_max_node_timeout_seconds: float = Field(
        default=300,
        gt=0,
        le=900,
        validation_alias="TASK_MAX_NODE_TIMEOUT_SECONDS",
    )
    task_max_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
        validation_alias="TASK_MAX_ATTEMPTS",
    )
    task_state_max_bytes: int = Field(
        default=65_536,
        ge=1024,
        le=1_048_576,
        validation_alias="TASK_STATE_MAX_BYTES",
    )
    task_stale_execution_seconds: int = Field(
        default=600,
        ge=30,
        le=86_400,
        validation_alias="TASK_STALE_EXECUTION_SECONDS",
    )

    shopee_partner_id: str | None = Field(default=None, validation_alias="SHOPEE_PARTNER_ID")
    shopee_partner_key: SecretStr | None = Field(
        default=None, validation_alias="SHOPEE_PARTNER_KEY"
    )
    shopee_shop_id: str | None = Field(default=None, validation_alias="SHOPEE_SHOP_ID")
    content_model_provider: Literal["offline_template", "aliyun_bailian"] = Field(
        default="offline_template", validation_alias="CONTENT_MODEL_PROVIDER"
    )
    bailian_api_key: SecretStr | None = Field(default=None, validation_alias="DASHSCOPE_API_KEY")
    bailian_base_url: str | None = Field(default=None, validation_alias="BAILIAN_BASE_URL")
    bailian_model: str = Field(default="qwen-plus", validation_alias="BAILIAN_MODEL")
    bailian_timeout_seconds: float = Field(
        default=30,
        gt=0,
        le=120,
        validation_alias="BAILIAN_TIMEOUT_SECONDS",
    )
    bailian_input_cost_per_million: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        validation_alias="BAILIAN_INPUT_COST_PER_MILLION",
    )
    bailian_output_cost_per_million: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        validation_alias="BAILIAN_OUTPUT_COST_PER_MILLION",
    )

    # ---- RAG LLM ----
    llm_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="LLM_API_KEY")
    llm_base_url: str = Field(default="https://api.openai.com/v1", validation_alias="LLM_BASE_URL")
    llm_model: str = Field(default="qwen-plus", validation_alias="LLM_MODEL")

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/'")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_security_and_platform(self) -> "Settings":
        if self.tool_default_timeout_seconds > self.tool_max_timeout_seconds:
            raise ValueError("Tool default timeout must not exceed the maximum timeout")
        if self.tool_retry_initial_delay_ms > self.tool_retry_max_delay_ms:
            raise ValueError("Tool retry initial delay must not exceed the maximum delay")
        if self.task_default_node_timeout_seconds > self.task_max_node_timeout_seconds:
            raise ValueError("Task default node timeout must not exceed the maximum timeout")

        jwt_secret = self.jwt_secret_key.get_secret_value()
        if self.app_env == "production" and (
            jwt_secret in EXAMPLE_JWT_SECRETS or len(jwt_secret) < 32
        ):
            raise ValueError(
                "Production requires a non-example JWT secret of at least 32 characters"
            )

        if self.platform_adapter == "real":
            required = (
                self.shopee_partner_id,
                self.shopee_partner_key.get_secret_value() if self.shopee_partner_key else None,
                self.shopee_shop_id,
            )
            if not all(required):
                raise ValueError(
                    "Real platform mode requires explicit Shopee configuration; "
                    "it never falls back to mock"
                )
        if self.content_model_provider == "aliyun_bailian":
            api_key = self.bailian_api_key.get_secret_value() if self.bailian_api_key else ""
            if not api_key or not self.bailian_base_url:
                raise ValueError(
                    "Aliyun Bailian mode requires DASHSCOPE_API_KEY and "
                    "BAILIAN_BASE_URL; it never silently falls back to offline output"
                )
            if not self.bailian_base_url.startswith("https://"):
                raise ValueError("BAILIAN_BASE_URL must use HTTPS")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
