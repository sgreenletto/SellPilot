import { afterEach, describe, expect, it, vi } from "vitest";

import { request } from "@/api/http";

describe("HTTP authentication handling", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("收到 401 时清除失效的本地登录信息", async () => {
    window.history.pushState({}, "", "/login");
    localStorage.setItem("sellpilot_token", "expired-token");
    localStorage.setItem("sellpilot_user", '{"username":"admin"}');
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "UNAUTHORIZED",
            message: "Unauthorized",
            data: null,
          }),
          {
            status: 401,
            headers: { "Content-Type": "application/json" },
          },
        ),
      ),
    );

    await expect(request("/v1/commerce/products")).rejects.toMatchObject({ status: 401 });
    expect(localStorage.getItem("sellpilot_token")).toBeNull();
    expect(localStorage.getItem("sellpilot_user")).toBeNull();
  });
});
