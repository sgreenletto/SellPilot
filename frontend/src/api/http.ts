import type { ApiResponse, FrontendApiErrorShape } from "@/api/types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
const DEFAULT_TIMEOUT_MS = 8_000;

export class FrontendApiError extends Error implements FrontendApiErrorShape {
  readonly code: string;
  readonly status: number;
  readonly requestId?: string;
  readonly details?: unknown;

  constructor(error: FrontendApiErrorShape) {
    super(error.message);
    this.name = "FrontendApiError";
    this.code = error.code;
    this.status = error.status;
    this.requestId = error.requestId;
    this.details = error.details;
  }
}

async function parseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  return response.json();
}

function getAuthHeaders(): Record<string, string> {
  try {
    const token = localStorage.getItem("sellpilot_token");
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
  } catch {
    // 无痕模式等静默忽略
  }
  return {};
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...getAuthHeaders(),
        ...init.headers,
      },
      signal: controller.signal,
    });
    const body = (await parseBody(response)) as Partial<ApiResponse<T>> | null;

    if (!response.ok || body?.code !== 0) {
      // 认证失效 → 清除旧 token 并跳转登录
      if (response.status === 401 || body?.code === "UNAUTHENTICATED") {
        try {
          localStorage.removeItem("sellpilot_token");
          localStorage.removeItem("sellpilot_user");
        } catch {
          /* noop */
        }
        window.location.href = "/login";
        throw new FrontendApiError({
          code: "UNAUTHENTICATED",
          message: "登录已过期，请重新登录",
          status: 401,
        });
      }
      throw new FrontendApiError({
        code: typeof body?.code === "string" ? body.code : "HTTP_ERROR",
        message: body?.message || `请求失败（${response.status}）`,
        status: response.status,
        requestId: body?.request_id,
        details: body?.data,
      });
    }

    if (!body || body.data === undefined || body.data === null) {
      throw new FrontendApiError({
        code: "INVALID_RESPONSE",
        message: "后端返回了无法识别的数据",
        status: response.status,
      });
    }

    return body.data;
  } catch (error: unknown) {
    if (error instanceof FrontendApiError) {
      throw error;
    }
    const message =
      error instanceof DOMException && error.name === "AbortError" ? "请求超时" : "后端未连接";
    throw new FrontendApiError({
      code: "NETWORK_ERROR",
      message,
      status: 0,
      details: error,
    });
  } finally {
    window.clearTimeout(timer);
  }
}
