from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from sellpilot.core.enums import (
    AfterSaleStatus,
    ConfirmationStatus,
    ContentType,
    ConversationStatus,
    CurrencyCode,
    DataSource,
    LanguageCode,
    LogisticsStatus,
    OperationStatus,
    OrderStatus,
    ProductStatus,
    ReportType,
    RiskLevel,
    SiteCode,
    SkuStatus,
    SortDirection,
    TaskStatus,
    TaskStepStatus,
    TaskType,
    ToolCallerType,
    ToolCallStatus,
    ToolRiskLevel,
    UserRole,
    WorkflowType,
)
from sellpilot.core.exceptions import ErrorCode, StateConflictError
from sellpilot.core.logging import SensitiveDataFilter
from sellpilot.core.middleware import request_id_context
from sellpilot.core.transitions import (
    CONFIRMATION_TRANSITIONS,
    TASK_TRANSITIONS,
    validate_confirmation_transition,
    validate_task_transition,
)
from sellpilot.schemas.common import (
    MAX_BATCH_SIZE,
    BatchRequest,
    LocalizedText,
    LocalizedTextSet,
    Money,
    PaginationParams,
    SourceMetadata,
)

EXPECTED_ENUM_VALUES = {
    ProductStatus: [
        "draft",
        "pending_confirmation",
        "published",
        "unpublished",
        "publish_failed",
        "archived",
    ],
    SkuStatus: ["active", "inactive", "out_of_stock", "archived"],
    DataSource: ["mock", "imported", "collected", "generated", "manual"],
    SiteCode: ["sg", "my", "ph", "th", "vn", "id", "tw", "br"],
    LanguageCode: ["zh-CN", "en", "ms", "id", "th", "vi", "tl", "pt-BR", "zh-TW"],
    CurrencyCode: ["CNY", "SGD", "MYR", "PHP", "THB", "VND", "IDR", "TWD", "BRL", "USD"],
    OrderStatus: [
        "pending",
        "paid",
        "processing",
        "shipped",
        "completed",
        "cancelled",
        "refunded",
    ],
    LogisticsStatus: [
        "pending",
        "ready_to_ship",
        "in_transit",
        "delivered",
        "exception",
        "returned",
    ],
    AfterSaleStatus: [
        "none",
        "requested",
        "processing",
        "approved",
        "rejected",
        "completed",
        "cancelled",
    ],
    ConversationStatus: ["open", "pending_reply", "pending_manual", "resolved", "closed"],
    RiskLevel: ["low", "medium", "high", "critical"],
    UserRole: ["ADMIN"],
    TaskStatus: [
        "pending",
        "running",
        "waiting_confirmation",
        "succeeded",
        "failed",
        "cancelled",
    ],
    TaskStepStatus: ["pending", "running", "succeeded", "failed", "cancelled"],
    ConfirmationStatus: [
        "pending",
        "confirmed",
        "executing",
        "succeeded",
        "failed",
        "cancelled",
    ],
    ToolCallStatus: [
        "pending",
        "running",
        "waiting_confirmation",
        "succeeded",
        "failed",
        "blocked",
        "timed_out",
    ],
    ToolRiskLevel: ["read", "write", "high_risk"],
    ToolCallerType: ["api", "agent", "workflow", "mcp", "system", "test"],
    OperationStatus: ["succeeded", "failed", "blocked", "timed_out"],
    TaskType: [
        "diagnostic",
        "data_import",
        "selection",
        "review_analysis",
        "product_improvement",
        "content_generation",
        "platform_operation",
        "knowledge_ingestion",
        "customer_service",
        "report_generation",
    ],
    WorkflowType: [
        "diagnostic",
        "selection",
        "review_analysis",
        "content_generation",
        "customer_service",
        "report_generation",
    ],
    ContentType: [
        "product_title",
        "product_description",
        "product_bullets",
        "customer_reply",
        "report",
    ],
    ReportType: ["selection", "review_analysis", "product_improvement", "operations"],
    SortDirection: ["asc", "desc"],
}


@pytest.mark.parametrize(
    ("enum_type", "expected"),
    EXPECTED_ENUM_VALUES.items(),
    ids=lambda value: getattr(value, "__name__", str(value)),
)
def test_public_enum_values_are_stable(enum_type, expected):
    assert [member.value for member in enum_type] == expected


class ProductStatusPayload(BaseModel):
    status: ProductStatus


def test_enum_json_serialization_uses_wire_value():
    payload = ProductStatusPayload(status=ProductStatus.PUBLISHED)
    assert payload.model_dump_json() == '{"status":"published"}'
    assert TypeAdapter(TaskStatus).dump_json(TaskStatus.WAITING_CONFIRMATION) == (
        b'"waiting_confirmation"'
    )


def test_legacy_foundation_status_values_remain_readable():
    assert TaskStatus("PENDING") is TaskStatus.PENDING
    assert ConfirmationStatus("CANCELED") is ConfirmationStatus.CANCELED
    assert ToolRiskLevel("HIGH_RISK") is ToolRiskLevel.HIGH_RISK


@pytest.mark.parametrize(
    "payload",
    [
        {"page": 0, "page_size": 20},
        {"page": 1, "page_size": 0},
        {"page": 1, "page_size": 101},
    ],
)
def test_pagination_parameters_reject_out_of_range_values(payload):
    with pytest.raises(ValidationError):
        PaginationParams.model_validate(payload)


def test_money_serializes_decimal_as_string_without_forcing_two_decimals():
    money = Money(amount=Decimal("1234"), currency=CurrencyCode.VND)
    assert money.model_dump_json() == '{"amount":"1234","currency":"VND"}'


@pytest.mark.parametrize("amount", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_money_rejects_non_finite_values(amount):
    with pytest.raises(ValidationError):
        Money(amount=amount, currency=CurrencyCode.USD)


def test_localized_text_rejects_blank_text_and_duplicate_languages():
    with pytest.raises(ValidationError):
        LocalizedText(language=LanguageCode.EN, text=" ")
    with pytest.raises(ValidationError, match="at most one text per language"):
        LocalizedTextSet(
            translations=[
                LocalizedText(language=LanguageCode.EN, text="First"),
                LocalizedText(language=LanguageCode.EN, text="Second"),
            ]
        )


def test_mock_source_must_be_explicitly_marked():
    with pytest.raises(ValidationError, match="is_mock=true"):
        SourceMetadata(
            source_type=DataSource.MOCK,
            source_name="synthetic fixture",
            collected_at=datetime.now(UTC),
        )


def test_api_datetime_rejects_timezone_free_wire_value():
    with pytest.raises(ValidationError):
        SourceMetadata(
            source_type=DataSource.IMPORTED,
            collected_at="2026-07-27T10:00:00",
        )


def test_request_id_is_added_to_log_record():
    import logging

    request_id = str(uuid4())
    token = request_id_context.set(request_id)
    try:
        record = logging.LogRecord(
            name="sellpilot.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="contract test",
            args=(),
            exc_info=None,
        )
        assert SensitiveDataFilter().filter(record) is True
        assert record.request_id == request_id
    finally:
        request_id_context.reset(token)


def test_batch_ids_cannot_be_empty():
    with pytest.raises(ValidationError):
        BatchRequest(ids=[], idempotency_key="batch:key")


def test_batch_ids_are_deduplicated_in_first_seen_order():
    first = uuid4()
    second = uuid4()
    request = BatchRequest(
        ids=[first, second, first],
        idempotency_key="batch:dedupe",
    )
    assert request.ids == [first, second]


def test_batch_size_is_bounded():
    with pytest.raises(ValidationError):
        BatchRequest(
            ids=[uuid4() for _ in range(MAX_BATCH_SIZE + 1)],
            idempotency_key="batch:oversized",
        )


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (current, target)
        for current, targets in TASK_TRANSITIONS.items()
        for target in targets
        if current is not TaskStatus.FAILED
    ],
)
def test_task_legal_transitions(current, target):
    validate_task_transition(current, target)


def test_task_retry_requires_explicit_authorization():
    with pytest.raises(StateConflictError, match="retry authorization"):
        validate_task_transition(TaskStatus.FAILED, TaskStatus.PENDING)
    validate_task_transition(
        TaskStatus.FAILED,
        TaskStatus.PENDING,
        allow_retry=True,
    )


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (TaskStatus.PENDING, TaskStatus.SUCCEEDED),
        (TaskStatus.SUCCEEDED, TaskStatus.RUNNING),
        (TaskStatus.CANCELLED, TaskStatus.PENDING),
        (TaskStatus.SUCCEEDED, TaskStatus.SUCCEEDED),
    ],
)
def test_task_illegal_or_terminal_repeated_transitions(current, target):
    with pytest.raises(StateConflictError):
        validate_task_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (current, target)
        for current, targets in CONFIRMATION_TRANSITIONS.items()
        for target in targets
    ],
)
def test_confirmation_legal_transitions(current, target):
    validate_confirmation_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ConfirmationStatus.PENDING, ConfirmationStatus.EXECUTING),
        (ConfirmationStatus.SUCCEEDED, ConfirmationStatus.EXECUTING),
        (ConfirmationStatus.FAILED, ConfirmationStatus.EXECUTING),
        (ConfirmationStatus.CANCELED, ConfirmationStatus.CONFIRMED),
        (ConfirmationStatus.SUCCEEDED, ConfirmationStatus.SUCCEEDED),
    ],
)
def test_confirmation_illegal_or_terminal_repeated_transitions(current, target):
    with pytest.raises(StateConflictError):
        validate_confirmation_transition(current, target)


def test_error_code_catalog_covers_required_categories():
    expected = {
        "PARAMETER_ERROR",
        "UNAUTHENTICATED",
        "PERMISSION_DENIED",
        "RESOURCE_NOT_FOUND",
        "STATE_CONFLICT",
        "DUPLICATE_OPERATION",
        "IDEMPOTENCY_CONFLICT",
        "DATA_IMPORT_FAILED",
        "MODEL_CALL_FAILED",
        "TOOL_FAILED",
        "WORKFLOW_FAILED",
        "MOCK_PLATFORM_FAILED",
        "EXTERNAL_SERVICE_UNAVAILABLE",
        "INTERNAL_ERROR",
    }
    assert expected <= {code.value for code in ErrorCode}
