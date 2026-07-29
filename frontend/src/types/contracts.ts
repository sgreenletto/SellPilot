export const PRODUCT_STATUSES = [
  "draft",
  "pending_confirmation",
  "published",
  "unpublished",
  "publish_failed",
  "archived",
] as const;
export type ProductStatus = (typeof PRODUCT_STATUSES)[number];

export const SKU_STATUSES = ["active", "inactive", "out_of_stock", "archived"] as const;
export type SkuStatus = (typeof SKU_STATUSES)[number];

export const DATA_SOURCES = ["mock", "imported", "collected", "generated", "manual"] as const;
export type DataSource = (typeof DATA_SOURCES)[number];

export const SITE_CODES = ["sg", "my", "ph", "th", "vn", "id", "tw", "br"] as const;
export type SiteCode = (typeof SITE_CODES)[number];

export const LANGUAGE_CODES = [
  "zh-CN",
  "en",
  "ms",
  "id",
  "th",
  "vi",
  "tl",
  "pt-BR",
  "zh-TW",
] as const;
export type LanguageCode = (typeof LANGUAGE_CODES)[number];

export const CURRENCY_CODES = [
  "CNY",
  "SGD",
  "MYR",
  "PHP",
  "THB",
  "VND",
  "IDR",
  "TWD",
  "BRL",
  "USD",
] as const;
export type CurrencyCode = (typeof CURRENCY_CODES)[number];

export const ORDER_STATUSES = [
  "pending",
  "paid",
  "processing",
  "shipped",
  "completed",
  "cancelled",
  "refunded",
] as const;
export type OrderStatus = (typeof ORDER_STATUSES)[number];

export const LOGISTICS_STATUSES = [
  "pending",
  "ready_to_ship",
  "in_transit",
  "delivered",
  "exception",
  "returned",
] as const;
export type LogisticsStatus = (typeof LOGISTICS_STATUSES)[number];

export const AFTER_SALE_STATUSES = [
  "none",
  "requested",
  "processing",
  "approved",
  "rejected",
  "completed",
  "cancelled",
] as const;
export type AfterSaleStatus = (typeof AFTER_SALE_STATUSES)[number];

export const CONVERSATION_STATUSES = [
  "open",
  "pending_reply",
  "pending_manual",
  "resolved",
  "closed",
] as const;
export type ConversationStatus = (typeof CONVERSATION_STATUSES)[number];

export const RISK_LEVELS = ["low", "medium", "high", "critical"] as const;
export type RiskLevel = (typeof RISK_LEVELS)[number];

export const TASK_STATUSES = [
  "pending",
  "running",
  "waiting_confirmation",
  "succeeded",
  "failed",
  "cancelled",
] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export const TASK_ACTIONS = ["run", "resume", "retry", "rerun", "cancel"] as const;
export type TaskAction = (typeof TASK_ACTIONS)[number];

export const TASK_STEP_STATUSES = [
  "pending",
  "running",
  "waiting_confirmation",
  "succeeded",
  "failed",
  "skipped",
  "cancelled",
] as const;
export type TaskStepStatus = (typeof TASK_STEP_STATUSES)[number];

export const WORKFLOW_NODE_TYPES = ["action", "tool", "branch", "loop", "wait", "finish"] as const;
export type WorkflowNodeType = (typeof WORKFLOW_NODE_TYPES)[number];

export const CONFIRMATION_STATUSES = [
  "pending",
  "confirmed",
  "executing",
  "succeeded",
  "failed",
  "cancelled",
] as const;
export type ConfirmationStatus = (typeof CONFIRMATION_STATUSES)[number];

export const TOOL_CALL_STATUSES = [
  "pending",
  "running",
  "waiting_confirmation",
  "succeeded",
  "failed",
  "blocked",
  "timed_out",
] as const;
export type ToolCallStatus = (typeof TOOL_CALL_STATUSES)[number];

export const TOOL_RISK_LEVELS = ["read", "write", "high_risk"] as const;
export type ToolRiskLevel = (typeof TOOL_RISK_LEVELS)[number];

export const TOOL_CALLER_TYPES = ["api", "agent", "workflow", "mcp", "system", "test"] as const;
export type ToolCallerType = (typeof TOOL_CALLER_TYPES)[number];

export const TASK_TYPES = [
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
  "replenishment",
] as const;
export type TaskType = (typeof TASK_TYPES)[number];

export const WORKFLOW_TYPES = [
  "diagnostic",
  "selection",
  "review_analysis",
  "content_generation",
  "customer_service",
  "report_generation",
] as const;
export type WorkflowType = (typeof WORKFLOW_TYPES)[number];

export const CONTENT_TYPES = [
  "product_title",
  "product_description",
  "product_bullets",
  "customer_reply",
  "report",
] as const;
export type ContentType = (typeof CONTENT_TYPES)[number];

export const REPORT_TYPES = [
  "selection",
  "review_analysis",
  "product_improvement",
  "operations",
] as const;
export type ReportType = (typeof REPORT_TYPES)[number];

export const ERROR_CODES = [
  "APP_ERROR",
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
  "TOOL_NOT_FOUND",
  "TOOL_DISABLED",
  "TOOL_ALREADY_REGISTERED",
  "TOOL_INPUT_INVALID",
  "TOOL_OUTPUT_INVALID",
  "TOOL_TIMEOUT",
  "TOOL_EXECUTION_FAILED",
  "TOOL_CONFIRMATION_REQUIRED",
  "TOOL_CONFIRMATION_INVALID",
  "TOOL_IDEMPOTENCY_CONFLICT",
  "TOOL_VERSION_CONFLICT",
  "TOOL_NOT_EXPOSED",
  "TOOL_RETRY_EXHAUSTED",
  "WORKFLOW_FAILED",
  "WORKFLOW_NOT_FOUND",
  "WORKFLOW_DISABLED",
  "WORKFLOW_ALREADY_REGISTERED",
  "WORKFLOW_VERSION_CONFLICT",
  "WORKFLOW_DEFINITION_INVALID",
  "TASK_NOT_FOUND",
  "TASK_NOT_RUNNABLE",
  "TASK_ALREADY_RUNNING",
  "TASK_NOT_RESUMABLE",
  "TASK_CONFIRMATION_PENDING",
  "TASK_CONFIRMATION_INVALID",
  "TASK_RETRY_NOT_ALLOWED",
  "TASK_ATTEMPT_EXHAUSTED",
  "TASK_CANCEL_NOT_ALLOWED",
  "TASK_STEP_NOT_FOUND",
  "TASK_NODE_TIMEOUT",
  "TASK_STATE_TOO_LARGE",
  "TASK_EXECUTION_CONFLICT",
  "MOCK_PLATFORM_FAILED",
  "EXTERNAL_SERVICE_UNAVAILABLE",
  "PLATFORM_NOT_CONFIGURED",
  "PLATFORM_FEATURE_NOT_IMPLEMENTED",
  "DATABASE_UNAVAILABLE",
  "CONFIRMATION_EXECUTOR_NOT_FOUND",
  "INTERNAL_ERROR",
] as const;
export type ApiErrorCode = (typeof ERROR_CODES)[number];

export interface ApiResponse<T> {
  code: number | string;
  message: string;
  data: T | null;
  request_id: string;
}

export interface ValidationIssue {
  field: string;
  message: string;
  type: string;
}

export type ApiErrorResponse = ApiResponse<ValidationIssue[]>;

export interface PaginationRequest {
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export type SortDirection = "asc" | "desc";

export interface SortRequest<TField extends string = string> {
  field: TField;
  direction?: SortDirection;
}

export interface CommonFilter<TStatus extends string = string> {
  search?: string;
  created_from?: string;
  created_to?: string;
  updated_from?: string;
  updated_to?: string;
  status?: TStatus;
  source?: DataSource;
}

export interface Money {
  amount: string;
  currency: CurrencyCode;
}

export interface LocalizedText {
  language: LanguageCode;
  text: string;
}

export interface LocalizedTextSet {
  translations: LocalizedText[];
}

export interface SourceMetadata {
  source_type: DataSource;
  source_name?: string | null;
  source_reference?: string | null;
  is_mock: boolean;
  collected_at?: string | null;
  generated_at?: string | null;
}

export interface BatchRequest {
  ids: string[];
  idempotency_key: string;
  note?: string | null;
}

export interface BatchItemFailure {
  id: string;
  error_code: string;
  message: string;
}

export interface BatchResult {
  total: number;
  succeeded: number;
  failed: number;
  failures: BatchItemFailure[];
}

export interface TaskSummary {
  task_id: string;
  status: TaskStatus;
  progress: number;
  current_step: string | null;
  message: string | null;
  error_code: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface WorkflowMetadata {
  name: string;
  version: string;
  description: string;
  task_type: TaskType;
  enabled: boolean;
  resumable: boolean;
  max_steps: number;
  max_task_attempts: number;
}

export interface TaskDetail {
  id: string;
  task_type: string;
  workflow_name: string;
  workflow_version: string;
  parent_task_id: string | null;
  status: TaskStatus;
  current_step: string | null;
  current_node: string | null;
  result: Record<string, unknown> | null;
  error_code: string | null;
  error_message: string | null;
  retry_count: number;
  task_attempt: number;
  request_id: string;
  created_by: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  updated_at: string;
  completed_at: string | null;
  waiting_confirmation: boolean;
  waiting_reason: string | null;
  safe_error_summary: string | null;
  available_actions: TaskAction[];
}

export interface TaskStepDetail {
  id: string;
  task_id: string;
  sequence: number;
  node_name: string;
  node_type: WorkflowNodeType;
  status: TaskStepStatus;
  attempt_count: number;
  input_summary: Record<string, unknown> | null;
  output_summary: Record<string, unknown> | null;
  error_code: string | null;
  error_message: string | null;
  tool_call_id: string | null;
  confirmation_id: string | null;
  metadata: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface TaskExecutionResult {
  task_id: string;
  workflow_name: string;
  workflow_version: string;
  status: TaskStatus;
  current_node: string | null;
  current_step_id: string | null;
  confirmation_required: boolean;
  confirmation_id: string | null;
  result: Record<string, unknown> | null;
  error_code: string | null;
  error_message: string | null;
  task_attempt: number;
  request_id: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ConfirmationSummary {
  id: string;
  agent_task_id: string;
  operation_type: string;
  target_type: string;
  target_id: string | null;
  risk_level: ToolRiskLevel;
  status: ConfirmationStatus;
  created_at: string;
}
