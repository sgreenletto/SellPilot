import { request } from "@/api/http";
import type { LoginRequest, LoginResponse } from "@/types/auth";

interface BackendTokenResponse {
  access_token: string;
  token_type: string;
}

interface BackendCurrentUser {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
}

export async function login(payload: LoginRequest): Promise<LoginResponse> {
  const tokenResponse = await request<BackendTokenResponse>("/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  const user = await request<BackendCurrentUser>("/v1/auth/me", {
    headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
  });
  return {
    token: tokenResponse.access_token,
    user: {
      id: user.id,
      username: user.username,
      displayName: user.username,
    },
  };
}
