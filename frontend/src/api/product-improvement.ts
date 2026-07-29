import { request } from "@/api/http";
import type {
  ConfirmationResult,
  ImprovementDraftItem,
  ImprovementDraftList,
  ImprovementReport,
  ImprovementSuggestion,
} from "@/types/product-improvement";

const auth = (method = "GET", body?: unknown): RequestInit => {
  const token = localStorage.getItem("sellpilot_token");
  return {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: body === undefined ? undefined : JSON.stringify(body),
  };
};

export const generateImprovementReport = (analysisId: string, forceRegenerate = false) =>
  request<ImprovementReport>(
    "/v1/product-improvement/reports",
    auth("POST", { analysis_id: analysisId, force_regenerate: forceRegenerate }),
    130_000,
  );

export const getImprovementReport = (reportId: string) =>
  request<ImprovementReport>(
    `/v1/product-improvement/reports/${encodeURIComponent(reportId)}`,
    auth(),
  );

export const updateImprovementSuggestion = (
  suggestionId: string,
  payload: Partial<Pick<ImprovementSuggestion, "title" | "description" | "status">>,
) =>
  request<ImprovementSuggestion>(
    `/v1/product-improvement/suggestions/${encodeURIComponent(suggestionId)}`,
    auth("PATCH", payload),
  );

export const exportImprovementReport = (reportId: string) =>
  request<{ filename: string; format: "markdown"; content: string }>(
    `/v1/product-improvement/reports/${encodeURIComponent(reportId)}/export`,
    auth(),
  );

export const requestImprovementDraft = (
  reportId: string,
  suggestionIds: string[],
  idempotencyKey: string,
  site: string,
) =>
  request<ConfirmationResult>(
    `/v1/product-improvement/reports/${encodeURIComponent(reportId)}/draft-confirmations`,
    auth("POST", {
      idempotency_key: idempotencyKey,
      site,
      target_language: "und",
      suggestion_ids: suggestionIds,
    }),
  );

export const confirmImprovementDraft = (confirmationId: string) =>
  request<ConfirmationResult>(
    `/v1/confirmations/${encodeURIComponent(confirmationId)}/confirm`,
    auth("POST"),
  );

export const cancelImprovementDraft = (confirmationId: string) =>
  request<ConfirmationResult>(
    `/v1/confirmations/${encodeURIComponent(confirmationId)}/cancel`,
    auth("POST"),
  );

export const listImprovementDrafts = (sourceProductId: string) =>
  request<ImprovementDraftList>(
    `/v1/product-improvement/drafts?source_product_id=${encodeURIComponent(sourceProductId)}`,
    auth(),
  );

export const requestImprovementDraftRevision = (
  versionId: string,
  expectedVersion: number,
  items: ImprovementDraftItem[],
  idempotencyKey: string,
) =>
  request<ConfirmationResult>(
    `/v1/product-improvement/drafts/${encodeURIComponent(versionId)}/revision-confirmations`,
    auth("POST", {
      idempotency_key: idempotencyKey,
      expected_version: expectedVersion,
      items,
    }),
  );

export const requestImprovementDraftHistoryClear = (
  sourceProductId: string,
  idempotencyKey: string,
) =>
  request<ConfirmationResult>(
    "/v1/product-improvement/drafts/clear-confirmations",
    auth("POST", {
      idempotency_key: idempotencyKey,
      source_product_id: sourceProductId,
    }),
  );
