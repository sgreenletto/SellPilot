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
    request.mockResolvedValueOnce({ access_token: "jwt-token", token_type: "bearer" });

    await expect(login({ username: "admin", password: "password123" })).resolves.toEqual({
      access_token: "jwt-token",
      token_type: "bearer",
    });
    expect(request).toHaveBeenNthCalledWith(1, "/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: "admin", password: "password123" }),
    });
  });
});
