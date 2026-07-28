from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

ProductTranslationLanguage = Literal["en", "zh-CN", "zh-TW", "ms", "id", "th", "vi", "tl", "pt-BR"]
ProductTranslationField = Literal["title", "description", "category_name", "specifications"]


class ProductTranslationSpecification(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=1000)


class ProductTranslationSource(BaseModel):
    product_id: str = Field(min_length=1, max_length=100)
    source_language: ProductTranslationLanguage
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=20000)
    category_name: str | None = Field(default=None, max_length=500)
    specifications: list[ProductTranslationSpecification] = Field(
        default_factory=list, max_length=100
    )


class ProductTranslationRequest(BaseModel):
    source: ProductTranslationSource
    target_languages: list[ProductTranslationLanguage] = Field(min_length=1, max_length=9)
    fields: list[ProductTranslationField] = Field(min_length=1, max_length=4)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def unique_targets_and_fields(self) -> "ProductTranslationRequest":
        if len(self.target_languages) != len(set(self.target_languages)):
            raise ValueError("target_languages must be unique")
        if self.source.source_language in self.target_languages:
            raise ValueError("target language must differ from source language")
        if len(self.fields) != len(set(self.fields)):
            raise ValueError("fields must be unique")
        return self


class ProductTranslationProviderStatus(BaseModel):
    configured: bool
    provider: str | None
    supported_languages: list[ProductTranslationLanguage]


class ProductTranslationResult(BaseModel):
    language: ProductTranslationLanguage
    title: str
    description: str
    category_name: str | None = None
    specifications: list[ProductTranslationSpecification]
    provider: str
    generated_at: datetime


class ProductTranslationFailure(BaseModel):
    language: ProductTranslationLanguage
    code: str
    message: str


class ProductTranslationTask(BaseModel):
    task_id: UUID
    confirmation_task_id: UUID
    status: Literal["pending_confirmation", "running", "succeeded", "partially_failed", "failed"]
    results: list[ProductTranslationResult]
    failed_languages: list[ProductTranslationFailure]
