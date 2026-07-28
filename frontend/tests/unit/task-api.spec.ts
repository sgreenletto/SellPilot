import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  cancelConfirmation,
  confirmConfirmation,
  listTaskOperationLogs,
  listTasks,
  resumeTask,
} from "@/api/tasks";
import { request } from "@/api/http";

vi.mock("@/api/http", () => ({
  request: vi.fn(),
}));

describe("task API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(request).mockResolvedValue({} as never);
  });

  it("only sends defined and non-empty task filters", async () => {
    await listTasks({
      page: 2,
      page_size: 20,
      status: "failed",
      workflow_name: "",
      task_type: undefined,
      created_from: null as never,
    });

    expect(vi.mocked(request).mock.calls[0]?.[0]).toBe(
      "/v1/tasks?page=2&page_size=20&status=failed",
    );
  });

  it("loads operation logs through the task-scoped endpoint", async () => {
    await listTaskOperationLogs("task/id", 3, 25);

    expect(vi.mocked(request).mock.calls[0]?.[0]).toBe(
      "/v1/tasks/task%2Fid/operation-logs?page=3&page_size=25",
    );
  });

  it("uses POST for task and confirmation operations", async () => {
    await resumeTask("task-1");
    await confirmConfirmation("confirmation-1");
    await cancelConfirmation("confirmation-2");

    expect(vi.mocked(request).mock.calls).toEqual([
      ["/v1/tasks/task-1/resume", { method: "POST" }],
      ["/v1/confirmations/confirmation-1/confirm", { method: "POST" }],
      ["/v1/confirmations/confirmation-2/cancel", { method: "POST" }],
    ]);
  });
});
