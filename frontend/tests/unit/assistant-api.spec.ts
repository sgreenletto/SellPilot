import { beforeEach, describe, expect, it, vi } from "vitest";

import { listAssistantCapabilities, planAssistantMessage } from "@/api/assistant";
import { request } from "@/api/http";

vi.mock("@/api/http", () => ({
  request: vi.fn(),
}));

describe("assistant API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(request).mockResolvedValue({} as never);
  });

  it("loads the server capability catalog", async () => {
    await listAssistantCapabilities();

    expect(vi.mocked(request)).toHaveBeenCalledWith("/v1/assistant/capabilities");
  });

  it("submits only the natural-language message to plan mode", async () => {
    await planAssistantMessage("查询订单 ORD000001 的物流");

    expect(vi.mocked(request)).toHaveBeenCalledWith("/v1/assistant/plan", {
      method: "POST",
      body: JSON.stringify({ message: "查询订单 ORD000001 的物流" }),
    });
  });
});
