import { request } from "@/api/http";
import type {
  ProductTranslationProviderStatus,
  ProductTranslationRequest,
  ProductTranslationTask,
} from "@/types/product-translation";

const TOKEN_KEY = "sellpilot_token";

function authInit(method = "GET", body?: unknown): RequestInit {
  const token = window.localStorage.getItem(TOKEN_KEY);
  return {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

export function getProductTranslationProviderStatus(): Promise<ProductTranslationProviderStatus> {
  return request<ProductTranslationProviderStatus>("/v1/product-translations/status", authInit());
}

export function requestProductTranslation(
  payload: ProductTranslationRequest,
): Promise<ProductTranslationTask> {
  return request<ProductTranslationTask>(
    "/v1/product-translations/requests",
    authInit("POST", payload),
  );
}

export function getProductTranslationTask(taskId: string): Promise<ProductTranslationTask> {
  return request<ProductTranslationTask>(
    `/v1/product-translations/tasks/${encodeURIComponent(taskId)}`,
    authInit(),
  );
}
