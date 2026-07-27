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
    """Application settings loaded from environment variables and backend/.env."""

    model_config = SettingsConfigDict(
        env_file=(REPOSITORY_ROOT / ".env", BACKEND_ROOT / ".env"),
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

    shopee_partner_id: str | None = Field(default=None, validation_alias="SHOPEE_PARTNER_ID")
    shopee_partner_key: SecretStr | None = Field(
        default=None, validation_alias="SHOPEE_PARTNER_KEY"
    )
    shopee_shop_id: str | None = Field(default=None, validation_alias="SHOPEE_SHOP_ID")

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/'")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_security_and_platform(self) -> "Settings":
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
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
