import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createAssistantTask,
  listAssistantCapabilities,
  listRecentAssistantTasks,
  planAssistantMessage,
} from "@/api/assistant";
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

  it("uses a separate Assistant task endpoint for create and run modes", async () => {
    await createAssistantTask(
      "检查 SHOP001 的低库存",
      "create_and_run",
      "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    );

    expect(vi.mocked(request)).toHaveBeenCalledWith("/v1/assistant/tasks", {
      method: "POST",
      headers: { "X-Request-ID": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" },
      body: JSON.stringify({
        message: "检查 SHOP001 的低库存",
        execution_mode: "create_and_run",
      }),
    });
  });

  it("loads only recent Assistant-created tasks", async () => {
    await listRecentAssistantTasks(7);

    expect(vi.mocked(request)).toHaveBeenCalledWith("/v1/assistant/tasks?limit=7");
  });
});
