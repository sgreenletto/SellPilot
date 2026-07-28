import { request } from "@/api/http";
import type { AuthUser, ChangePasswordRequest, LoginRequest, LoginResponse } from "@/types/auth";

export function login(payload: LoginRequest): Promise<LoginResponse> {
  return request<LoginResponse>("/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function me(): Promise<AuthUser> {
  return request<AuthUser>("/v1/auth/me");
}

export function changePassword(payload: ChangePasswordRequest): Promise<AuthUser> {
  return request<AuthUser>("/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
