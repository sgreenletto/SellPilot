import { request } from "@/api/http";
import type {
  SelectionAnalysis,
  SelectionAnalysisRequest,
  SelectionCandidate,
  SelectionCandidateQuery,
  SelectionExport,
  SelectionResult,
  SelectionTask,
} from "@/types/selection";

const TOKEN_KEY = "sellpilot_token";

function authInit(method = "GET", body?: unknown): RequestInit {
  const token = window.localStorage.getItem(TOKEN_KEY);
  return {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

export function selectionQueryString(query: SelectionCandidateQuery): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === "" || value === null) continue;
    if (Array.isArray(value)) {
      value.forEach((item) => params.append(key === "product_ids" ? "product_id" : key, item));
    } else {
      params.set(key, String(value));
    }
  }
  const serialized = params.toString();
  return serialized ? `?${serialized}` : "";
}

export function listSelectionCandidates(
  query: SelectionCandidateQuery,
): Promise<SelectionCandidate[]> {
  return request<SelectionCandidate[]>(
    `/v1/selection/candidates${selectionQueryString(query)}`,
    authInit(),
  );
}

export function createSelectionAnalysis(
  payload: SelectionAnalysisRequest,
): Promise<SelectionAnalysis> {
  return request<SelectionAnalysis>("/v1/selection/analyses", authInit("POST", payload), 30_000);
}

export function getSelectionAnalysis(taskId: string): Promise<SelectionTask> {
  return request<SelectionTask>(`/v1/selection/analyses/${encodeURIComponent(taskId)}`, authInit());
}

export function compareSelectionProducts(
  taskId: string,
  productIds: string[],
): Promise<SelectionResult[]> {
  const params = new URLSearchParams();
  productIds.forEach((productId) => params.append("product_id", productId));
  return request<SelectionResult[]>(
    `/v1/selection/analyses/${encodeURIComponent(taskId)}/compare?${params.toString()}`,
    authInit(),
  );
}

export function exportSelectionAnalysis(taskId: string): Promise<SelectionExport> {
  return request<SelectionExport>(
    `/v1/selection/analyses/${encodeURIComponent(taskId)}/export`,
    authInit(),
  );
}

export function downloadSelectionExport(report: SelectionExport): void {
  const blob = new Blob([JSON.stringify(report.task, null, 2)], {
    type: report.content_type,
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = report.filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
