import { request } from "@/api/http";
import type { TaskDetail, TaskStatus, ToolRiskLevel } from "@/types/contracts";

export type AssistantAvailability = "available" | "contract_only" | "unavailable";
export type AssistantIntent =
  | "selection_analysis"
  | "review_analysis"
  | "product_improvement"
  | "content_generation"
  | "inventory_replenishment"
  | "low_stock_check"
  | "order_query"
  | "logistics_query"
  | "knowledge_query"
  | "customer_service_reply"
  | "unknown";

export interface AssistantCapability {
  capability_key: string;
  display_name: string;
  intent: Exclude<AssistantIntent, "unknown">;
  workflow_name: string | null;
  workflow_version: string | null;
  required_parameters: string[];
  optional_parameters: string[];
  tool_names: string[];
  risk_level: ToolRiskLevel;
  requires_confirmation: boolean;
  availability: AssistantAvailability;
  unavailable_reason: string | null;
  example_message: string;
  target_path: string;
}

export interface AssistantPlanStep {
  order: number;
  kind: "workflow" | "tool" | "capability";
  name: string;
  summary: string;
}

export interface AssistantPlan {
  detected_intent: AssistantIntent;
  extracted_parameters: Record<string, unknown>;
  missing_parameters: string[];
  selected_capability: string | null;
  selected_workflow: { name: string; version: string } | null;
  tool_names: string[];
  steps: AssistantPlanStep[];
  risk_summary: string;
  requires_confirmation: boolean;
  availability: AssistantAvailability;
  unavailable_reason: string | null;
  can_execute: boolean;
  target_path: string | null;
  mock_mode: boolean;
  mock_notice: string;
}

export type AssistantExecutionMode = "create_only" | "create_and_run";

export interface AssistantTaskResult {
  detected_intent: AssistantIntent;
  selected_capability: string;
  workflow_name: string;
  workflow_version: string;
  plan: AssistantPlan;
  task_id: string;
  task_status: TaskStatus;
  execution_mode: AssistantExecutionMode;
  confirmation_required: boolean;
  confirmation_id: string | null;
  duplicate: boolean;
  created_at: string;
}

export function listAssistantCapabilities(): Promise<AssistantCapability[]> {
  return request<AssistantCapability[]>("/v1/assistant/capabilities");
}

export function planAssistantMessage(message: string): Promise<AssistantPlan> {
  return request<AssistantPlan>("/v1/assistant/plan", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export function createAssistantTask(
  message: string,
  executionMode: AssistantExecutionMode,
): Promise<AssistantTaskResult> {
  return request<AssistantTaskResult>("/v1/assistant/tasks", {
    method: "POST",
    body: JSON.stringify({ message, execution_mode: executionMode }),
  });
}

export function listRecentAssistantTasks(limit = 5): Promise<TaskDetail[]> {
  return request<TaskDetail[]>(`/v1/assistant/tasks?limit=${limit}`);
}
