import { beforeEach, describe, expect, it, vi } from "vitest";

import { login } from "@/api/auth";

const request = vi.fn();

vi.mock("@/api/http", () => ({
  request: (...args: unknown[]) => request(...args),
}));

describe("auth API", () => {
  beforeEach(() => {
    request.mockReset();
  });

  it("使用真实后端令牌读取当前用户", async () => {
    request
      .mockResolvedValueOnce({ access_token: "jwt-token", token_type: "bearer" })
      .mockResolvedValueOnce({
        id: "user-id",
        username: "admin",
        role: "admin",
        is_active: true,
      });

    await expect(login({ username: "admin", password: "password123" })).resolves.toEqual({
      token: "jwt-token",
      user: {
        id: "user-id",
        username: "admin",
        displayName: "admin",
      },
    });
    expect(request).toHaveBeenNthCalledWith(1, "/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: "admin", password: "password123" }),
    });
    expect(request).toHaveBeenNthCalledWith(2, "/v1/auth/me", {
      headers: { Authorization: "Bearer jwt-token" },
    });
  });
});
