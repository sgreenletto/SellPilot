import { request } from "@/api/http"
import type { LoginRequest, LoginResponse } from "@/types/auth"

/** 调用后端 POST /api/v1/auth/login，返回真实 JWT */
export function login(payload: LoginRequest): Promise<LoginResponse> {
  return request<LoginResponse>("/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}
