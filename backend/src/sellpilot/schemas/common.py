from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from sellpilot.core.enums import CurrencyCode, DataSource, LanguageCode, SortDirection

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_BATCH_SIZE = 100

IdempotencyKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=8,
        max_length=255,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]
MoneyAmount = Annotated[
    Decimal,
    Field(max_digits=38, decimal_places=18, allow_inf_nan=False),
]


def _attach_utc_to_legacy_datetime(value: object) -> object:
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


ApiDateTime = Annotated[
    AwareDatetime,
    BeforeValidator(_attach_utc_to_legacy_datetime),
]


class ContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class IdentityFields(ContractModel):
    id: UUID


class TimestampFields(ContractModel):
    created_at: ApiDateTime
    updated_at: ApiDateTime

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> "TimestampFields":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        return self


class AuditFields(ContractModel):
    created_by: UUID | None = None
    updated_by: UUID | None = None


class Money(ContractModel):
    amount: MoneyAmount
    currency: CurrencyCode


class LocalizedText(ContractModel):
    language: LanguageCode
    text: str = Field(min_length=1, max_length=20_000)


class LocalizedTextSet(ContractModel):
    translations: list[LocalizedText] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_unique_languages(self) -> "LocalizedTextSet":
        languages = [item.language for item in self.translations]
        if len(languages) != len(set(languages)):
            raise ValueError("translations must contain at most one text per language")
        return self


class SourceMetadata(ContractModel):
    source_type: DataSource
    source_name: str | None = Field(default=None, min_length=1, max_length=200)
    source_reference: str | None = Field(default=None, min_length=1, max_length=500)
    is_mock: bool = False
    collected_at: ApiDateTime | None = None
    generated_at: ApiDateTime | None = None

    @model_validator(mode="after")
    def validate_mock_marker(self) -> "SourceMetadata":
        if self.source_type is DataSource.MOCK and not self.is_mock:
            raise ValueError("mock source data must set is_mock=true")
        return self


class PaginationParams(ContractModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)


class SortParams(ContractModel):
    field: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    direction: SortDirection = SortDirection.ASC


class CommonFilter(ContractModel):
    search: str | None = Field(default=None, min_length=1, max_length=200)
    created_from: ApiDateTime | None = None
    created_to: ApiDateTime | None = None
    updated_from: ApiDateTime | None = None
    updated_to: ApiDateTime | None = None
    status: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    source: DataSource | None = None

    @model_validator(mode="after")
    def validate_time_ranges(self) -> "CommonFilter":
        if (
            self.created_from is not None
            and self.created_to is not None
            and self.created_from > self.created_to
        ):
            raise ValueError("created_from must not be later than created_to")
        if (
            self.updated_from is not None
            and self.updated_to is not None
            and self.updated_from > self.updated_to
        ):
            raise ValueError("updated_from must not be later than updated_to")
        return self


class BatchRequest(ContractModel):
    ids: list[UUID] = Field(min_length=1, max_length=MAX_BATCH_SIZE)
    idempotency_key: IdempotencyKey
    note: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("ids")
    @classmethod
    def deduplicate_ids(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))


class BatchItemFailure(ContractModel):
    id: UUID
    error_code: str = Field(min_length=1, max_length=100, pattern=r"^[A-Z][A-Z0-9_]*$")
    message: str = Field(min_length=1, max_length=500)


class BatchResult(ContractModel):
    total: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    failures: list[BatchItemFailure] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts(self) -> "BatchResult":
        if self.total != self.succeeded + self.failed:
            raise ValueError("total must equal succeeded plus failed")
        if self.failed != len(self.failures):
            raise ValueError("failed must equal the number of failure details")
        return self


AllowedFileContentType = Literal[
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
]


class FileUploadResult(ContractModel):
    file_id: UUID
    original_name: str = Field(min_length=1, max_length=255)
    safe_name: str = Field(min_length=1, max_length=255)
    content_type: AllowedFileContentType
    size_bytes: int = Field(ge=1)
    checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    is_mock: bool = False
