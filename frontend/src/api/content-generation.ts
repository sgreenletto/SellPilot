import { request } from "@/api/http";
import type {
  ContentConfirmation,
  ContentGeneration,
  ContentVersions,
} from "@/types/content-generation";

const auth = (method = "GET", body?: unknown): RequestInit => {
  const token = localStorage.getItem("sellpilot_token");
  return {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: body === undefined ? undefined : JSON.stringify(body),
  };
};
export const generateContent = (payload: Record<string, unknown>) =>
  request<ContentGeneration>("/v1/content-generation/generate", auth("POST", payload), 30_000);
export const requestContentDraft = (generation: ContentGeneration, idempotencyKey: string) =>
  request<ContentConfirmation>(
    "/v1/content-generation/draft-confirmations",
    auth("POST", { idempotency_key: idempotencyKey, generation }),
  );
export const confirmContentDraft = (id: string) =>
  request<ContentConfirmation>(`/v1/confirmations/${encodeURIComponent(id)}/confirm`, auth("POST"));
export const cancelContentDraft = (id: string) =>
  request<ContentConfirmation>(`/v1/confirmations/${encodeURIComponent(id)}/cancel`, auth("POST"));
export const listContentVersions = (id: string) =>
  request<ContentVersions>(
    `/v1/content-generation/contents/${encodeURIComponent(id)}/versions`,
    auth(),
  );
export const requestVersionRestore = (contentId: string, versionId: string, key: string) =>
  request<ContentConfirmation>(
    `/v1/content-generation/contents/${encodeURIComponent(contentId)}/restore-confirmations`,
    auth("POST", { idempotency_key: key, version_id: versionId }),
  );
