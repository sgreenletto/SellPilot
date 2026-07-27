from enum import StrEnum


class _LegacyLowerStrEnum(StrEnum):
    """Lowercase wire values with read compatibility for v0.1.0 uppercase rows."""

    @classmethod
    def _missing_(cls, value: object):
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()
        if normalized == "canceled":
            normalized = "cancelled"
        return next((member for member in cls if member.value == normalized), None)


class UserRole(StrEnum):
    # Kept uppercase for compatibility with the existing authentication contract.
    ADMIN = "ADMIN"


class ProductStatus(StrEnum):
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    PUBLISH_FAILED = "publish_failed"
    ARCHIVED = "archived"


class SkuStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    ARCHIVED = "archived"


class DataSource(StrEnum):
    MOCK = "mock"
    IMPORTED = "imported"
    COLLECTED = "collected"
    GENERATED = "generated"
    MANUAL = "manual"


class SiteCode(StrEnum):
    SG = "sg"
    MY = "my"
    PH = "ph"
    TH = "th"
    VN = "vn"
    ID = "id"
    TW = "tw"
    BR = "br"


class LanguageCode(StrEnum):
    ZH_CN = "zh-CN"
    EN = "en"
    MS = "ms"
    ID = "id"
    TH = "th"
    VI = "vi"
    TL = "tl"
    PT_BR = "pt-BR"
    ZH_TW = "zh-TW"


class CurrencyCode(StrEnum):
    CNY = "CNY"
    SGD = "SGD"
    MYR = "MYR"
    PHP = "PHP"
    THB = "THB"
    VND = "VND"
    IDR = "IDR"
    TWD = "TWD"
    BRL = "BRL"
    USD = "USD"


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class LogisticsStatus(StrEnum):
    PENDING = "pending"
    READY_TO_SHIP = "ready_to_ship"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    RETURNED = "returned"


class AfterSaleStatus(StrEnum):
    NONE = "none"
    REQUESTED = "requested"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ConversationStatus(StrEnum):
    OPEN = "open"
    PENDING_REPLY = "pending_reply"
    PENDING_MANUAL = "pending_manual"
    RESOLVED = "resolved"
    CLOSED = "closed"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnalysisStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class ImprovementReportStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    ARCHIVED = "ARCHIVED"


class ImprovementSuggestionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    IGNORED = "IGNORED"
    ARCHIVED = "ARCHIVED"


class ProductContentStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class PromptStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class ModelInvocationStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class GeneratedReportStatus(StrEnum):
    READY = "READY"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class TaskStatus(_LegacyLowerStrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_CONFIRMATION = "waiting_confirmation"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStepStatus(_LegacyLowerStrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolCallStatus(_LegacyLowerStrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    TIMED_OUT = "timed_out"


class ConfirmationStatus(_LegacyLowerStrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "cancelled"


class OperationStatus(_LegacyLowerStrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ToolRiskLevel(_LegacyLowerStrEnum):
    READ = "read"
    WRITE = "write"
    HIGH_RISK = "high_risk"


class TaskType(StrEnum):
    DIAGNOSTIC = "diagnostic"
    DATA_IMPORT = "data_import"
    SELECTION = "selection"
    REVIEW_ANALYSIS = "review_analysis"
    PRODUCT_IMPROVEMENT = "product_improvement"
    CONTENT_GENERATION = "content_generation"
    PLATFORM_OPERATION = "platform_operation"
    KNOWLEDGE_INGESTION = "knowledge_ingestion"
    CUSTOMER_SERVICE = "customer_service"
    REPORT_GENERATION = "report_generation"


class WorkflowType(StrEnum):
    DIAGNOSTIC = "diagnostic"
    SELECTION = "selection"
    REVIEW_ANALYSIS = "review_analysis"
    CONTENT_GENERATION = "content_generation"
    CUSTOMER_SERVICE = "customer_service"
    REPORT_GENERATION = "report_generation"


class ContentType(StrEnum):
    PRODUCT_TITLE = "product_title"
    PRODUCT_DESCRIPTION = "product_description"
    PRODUCT_BULLETS = "product_bullets"
    CUSTOMER_REPLY = "customer_reply"
    REPORT = "report"


class ReportType(StrEnum):
    SELECTION = "selection"
    REVIEW_ANALYSIS = "review_analysis"
    PRODUCT_IMPROVEMENT = "product_improvement"
    OPERATIONS = "operations"


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"
