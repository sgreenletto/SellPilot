import { request } from "@/api/http";
import type {
  ConfirmationStatus,
  PaginatedResponse,
  TaskAction,
  TaskDetail,
  TaskExecutionResult,
  TaskStatus,
  TaskStepDetail,
  ToolCallerType,
  ToolCallStatus,
  ToolRiskLevel,
} from "@/types/contracts";

export interface TaskListFilters {
  page?: number;
  page_size?: number;
  status?: TaskStatus;
  workflow_name?: string;
  task_type?: string;
  created_from?: string;
  created_to?: string;
}

export interface TaskConfirmation {
  id: string;
  agent_task_id: string;
  task_step_id: string | null;
  operation_type: string;
  target_type: string;
  target_id: string | null;
  risk_level: ToolRiskLevel;
  before_snapshot: Record<string, unknown> | null;
  after_snapshot: Record<string, unknown> | null;
  status: ConfirmationStatus;
  idempotency_key: string;
  created_by: string;
  confirmed_by: string | null;
  created_at: string;
  confirmed_at: string | null;
  execution_started_at: string | null;
  executed_at: string | null;
  execution_result: Record<string, unknown> | null;
  error_message: string | null;
  risk_warning: string | null;
}

export interface TaskToolCall {
  id: string;
  tool_name: string;
  tool_version: string;
  risk_level: ToolRiskLevel;
  caller_type: ToolCallerType;
  caller_name: string | null;
  request_id: string;
  user_id: string | null;
  task_id: string | null;
  task_step_id: string | null;
  confirmation_id: string | null;
  input_summary: Record<string, unknown> | null;
  output_summary: Record<string, unknown> | null;
  attempt_history: Record<string, unknown> | null;
  status: ToolCallStatus;
  attempt_count: number;
  duration_ms: number | null;
  error_code: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
}

export interface TaskOperationLog {
  id: string;
  event_type: string;
  description: string;
  status: "succeeded" | "failed" | "blocked" | "timed_out";
  task_id: string | null;
  task_step_id: string | null;
  tool_call_id: string | null;
  confirmation_id: string | null;
  actor: Record<string, unknown> | null;
  request_id: string;
  created_at: string;
  metadata: Record<string, unknown> | null;
}

function queryString(params: object): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

function post<T>(path: string): Promise<T> {
  return request<T>(path, { method: "POST" });
}

export function createTask(
  workflowName: string,
  workflowInput: Record<string, unknown>,
): Promise<TaskDetail> {
  return request<TaskDetail>("/v1/tasks", {
    method: "POST",
    body: JSON.stringify({
      workflow_name: workflowName,
      workflow_input: workflowInput,
    }),
  });
}

export function listTasks(filters: TaskListFilters = {}): Promise<PaginatedResponse<TaskDetail>> {
  return request<PaginatedResponse<TaskDetail>>(`/v1/tasks${queryString(filters)}`);
}

export function getTask(taskId: string): Promise<TaskDetail> {
  return request<TaskDetail>(`/v1/tasks/${encodeURIComponent(taskId)}`);
}

export function listTaskSteps(taskId: string): Promise<TaskStepDetail[]> {
  return request<TaskStepDetail[]>(`/v1/tasks/${encodeURIComponent(taskId)}/steps`);
}

export function listTaskToolCalls(
  taskId: string,
  page = 1,
  pageSize = 100,
): Promise<PaginatedResponse<TaskToolCall>> {
  return request<PaginatedResponse<TaskToolCall>>(
    `/v1/tool-calls${queryString({ task_id: taskId, page, page_size: pageSize })}`,
  );
}

export function listTaskConfirmations(
  taskId: string,
  page = 1,
  pageSize = 100,
): Promise<PaginatedResponse<TaskConfirmation>> {
  return request<PaginatedResponse<TaskConfirmation>>(
    `/v1/confirmations${queryString({ task_id: taskId, page, page_size: pageSize })}`,
  );
}

export function listTaskOperationLogs(
  taskId: string,
  page = 1,
  pageSize = 100,
): Promise<PaginatedResponse<TaskOperationLog>> {
  return request<PaginatedResponse<TaskOperationLog>>(
    `/v1/tasks/${encodeURIComponent(taskId)}/operation-logs${queryString({
      page,
      page_size: pageSize,
    })}`,
  );
}

export function runTask(taskId: string): Promise<TaskExecutionResult> {
  return post<TaskExecutionResult>(`/v1/tasks/${encodeURIComponent(taskId)}/run`);
}

export function resumeTask(taskId: string): Promise<TaskExecutionResult> {
  return post<TaskExecutionResult>(`/v1/tasks/${encodeURIComponent(taskId)}/resume`);
}

export function retryTask(taskId: string): Promise<TaskExecutionResult> {
  return post<TaskExecutionResult>(`/v1/tasks/${encodeURIComponent(taskId)}/retry`);
}

export function rerunTask(taskId: string): Promise<TaskDetail> {
  return post<TaskDetail>(`/v1/tasks/${encodeURIComponent(taskId)}/rerun`);
}

export function cancelTask(taskId: string): Promise<TaskDetail> {
  return post<TaskDetail>(`/v1/tasks/${encodeURIComponent(taskId)}/cancel`);
}

export function confirmConfirmation(confirmationId: string): Promise<TaskConfirmation> {
  return post<TaskConfirmation>(`/v1/confirmations/${encodeURIComponent(confirmationId)}/confirm`);
}

export function cancelConfirmation(confirmationId: string): Promise<TaskConfirmation> {
  return post<TaskConfirmation>(`/v1/confirmations/${encodeURIComponent(confirmationId)}/cancel`);
}

export type { TaskAction };
