import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as taskApi from "@/api/tasks";
import { FrontendApiError } from "@/api/http";
import type { TaskConfirmation, TaskOperationLog, TaskToolCall } from "@/api/tasks";
import { router as applicationRouter } from "@/router";
import type { TaskDetail, TaskStepDetail } from "@/types/contracts";
import TaskCenterView from "@/views/tasks/TaskCenterView.vue";

vi.mock("@/api/tasks", () => ({
  cancelConfirmation: vi.fn(),
  cancelTask: vi.fn(),
  confirmConfirmation: vi.fn(),
  getTask: vi.fn(),
  listTaskConfirmations: vi.fn(),
  listTaskOperationLogs: vi.fn(),
  listTaskSteps: vi.fn(),
  listTasks: vi.fn(),
  listTaskToolCalls: vi.fn(),
  rerunTask: vi.fn(),
  resumeTask: vi.fn(),
  retryTask: vi.fn(),
  runTask: vi.fn(),
}));

const task: TaskDetail = {
  id: "task-1",
  task_type: "diagnostic",
  workflow_name: "diagnostic",
  workflow_version: "1.0.0",
  parent_task_id: null,
  status: "waiting_confirmation",
  current_step: "publish",
  current_node: "publish",
  result: null,
  error_code: null,
  error_message: null,
  retry_count: 0,
  task_attempt: 1,
  request_id: "request-1",
  created_by: "user-1",
  created_at: "2026-07-28T10:00:00Z",
  started_at: "2026-07-28T10:00:01Z",
  finished_at: null,
  updated_at: "2026-07-28T10:00:01Z",
  completed_at: null,
  waiting_confirmation: true,
  waiting_reason: "等待用户确认",
  safe_error_summary: null,
  available_actions: ["cancel"],
};

const step: TaskStepDetail = {
  id: "step-1",
  task_id: task.id,
  sequence: 1,
  node_name: "publish",
  node_type: "tool",
  status: "waiting_confirmation",
  attempt_count: 1,
  input_summary: { product_id: "synthetic-product" },
  output_summary: null,
  error_code: null,
  error_message: null,
  tool_call_id: "call-1",
  confirmation_id: "confirmation-1",
  metadata: null,
  started_at: task.started_at,
  completed_at: null,
};

const confirmation: TaskConfirmation = {
  id: "confirmation-1",
  agent_task_id: task.id,
  task_step_id: step.id,
  operation_type: "tool.execute",
  target_type: "product",
  target_id: "synthetic-product",
  risk_level: "write",
  before_snapshot: { title: "before" },
  after_snapshot: { title: "after" },
  status: "pending",
  idempotency_key: "safe-test-key",
  created_by: "user-1",
  confirmed_by: null,
  created_at: task.created_at,
  confirmed_at: null,
  execution_started_at: null,
  executed_at: null,
  execution_result: null,
  error_message: null,
  risk_warning: "请核对变更",
};

const toolCall: TaskToolCall = {
  id: "call-1",
  tool_name: "mock_publish",
  tool_version: "1.0.0",
  risk_level: "write",
  caller_type: "workflow",
  caller_name: "diagnostic",
  request_id: task.request_id,
  user_id: "user-1",
  task_id: task.id,
  task_step_id: step.id,
  confirmation_id: confirmation.id,
  input_summary: { product_id: "synthetic-product" },
  output_summary: null,
  attempt_history: null,
  status: "waiting_confirmation",
  attempt_count: 1,
  duration_ms: 12,
  error_code: null,
  error_message: null,
  started_at: task.started_at ?? task.created_at,
  completed_at: null,
  created_at: task.created_at,
};

const operationLog: TaskOperationLog = {
  id: "log-1",
  event_type: "confirmation_requested",
  description: "等待安全确认",
  status: "succeeded",
  task_id: task.id,
  task_step_id: step.id,
  tool_call_id: toolCall.id,
  confirmation_id: confirmation.id,
  actor: { id: "user-1" },
  request_id: task.request_id,
  created_at: task.created_at,
  metadata: { safe: true },
};

function page<T>(items: T[]) {
  return { items, total: items.length, page: 1, page_size: 20, pages: 1 };
}

async function mountView(query = "") {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/tasks", component: TaskCenterView }],
  });
  await router.push(`/tasks${query}`);
  await router.isReady();
  const wrapper = mount(TaskCenterView, { global: { plugins: [router] } });
  await flushPromises();
  return wrapper;
}

describe("TaskCenterView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(taskApi.listTasks).mockResolvedValue(page([task]));
    vi.mocked(taskApi.getTask).mockResolvedValue(task);
    vi.mocked(taskApi.listTaskSteps).mockResolvedValue([step]);
    vi.mocked(taskApi.listTaskToolCalls).mockResolvedValue(page([toolCall]));
    vi.mocked(taskApi.listTaskConfirmations).mockResolvedValue(page([confirmation]));
    vi.mocked(taskApi.listTaskOperationLogs).mockResolvedValue(page([operationLog]));
    vi.mocked(taskApi.confirmConfirmation).mockResolvedValue({
      ...confirmation,
      status: "succeeded",
    });
    Object.defineProperty(window, "confirm", {
      configurable: true,
      value: vi.fn(() => true),
    });
  });

  it("loads the real task list and supports an empty state", async () => {
    const wrapper = await mountView();
    expect(wrapper.text()).toContain("运行诊断");
    expect(wrapper.text()).toContain("等待确认");
    expect(wrapper.text()).not.toContain("TaskWorkflowRuntime");
    expect(wrapper.text()).not.toContain(
      "查看任务进度、确认风险操作，并按服务端允许的操作继续执行。",
    );
    expect(wrapper.findAll("h1")).toHaveLength(0);

    vi.mocked(taskApi.listTasks).mockResolvedValueOnce(page([]));
    const refresh = wrapper.findAll("button").find((button) => button.text() === "刷新");
    await refresh?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("暂无任务");
  });

  it("restores task_id and loads detail resources in parallel", async () => {
    const wrapper = await mountView("?task_id=task-1");

    expect(taskApi.getTask).toHaveBeenCalledWith("task-1");
    expect(taskApi.listTaskSteps).toHaveBeenCalledWith("task-1");
    expect(taskApi.listTaskToolCalls).toHaveBeenCalledWith("task-1");
    expect(taskApi.listTaskConfirmations).toHaveBeenCalledWith("task-1");
    expect(taskApi.listTaskOperationLogs).toHaveBeenCalledWith("task-1");
    expect(wrapper.text()).toContain("模拟发布商品");
    expect(wrapper.text()).toContain("等待安全确认");
    expect(wrapper.text()).toContain("synthetic-product");
    expect(wrapper.text()).not.toContain("serialized_state");
    expect(wrapper.findAll("button").some((button) => button.text() === "继续")).toBe(false);
    expect(wrapper.findAll("button").some((button) => button.text() === "取消")).toBe(true);
  });

  it("submits localized filters with their original API values", async () => {
    const wrapper = await mountView();
    const [statusSelect] = wrapper.findAll("select");
    await statusSelect?.setValue("succeeded");
    const applyButton = wrapper.findAll("button").find((button) => button.text() === "应用筛选");
    await applyButton?.trigger("click");
    await flushPromises();

    expect(taskApi.listTasks).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: "succeeded" }),
    );
    expect(wrapper.text()).toContain("已完成");
    expect(wrapper.text()).not.toContain("succeeded");
  });

  it("requires explicit confirmation and refreshes after confirming", async () => {
    const wrapper = await mountView("?task_id=task-1");
    const confirmButton = wrapper.findAll("button").find((button) => button.text() === "确认执行");
    await confirmButton?.trigger("click");
    await flushPromises();

    expect(window.confirm).toHaveBeenCalled();
    expect(taskApi.confirmConfirmation).toHaveBeenCalledWith("confirmation-1");
    expect(taskApi.listTasks).toHaveBeenCalledTimes(2);
  });

  it("locks task action buttons while an operation is running", async () => {
    let resolveCancel: (value: TaskDetail) => void = () => undefined;
    vi.mocked(taskApi.cancelTask).mockImplementationOnce(
      () =>
        new Promise<TaskDetail>((resolve) => {
          resolveCancel = resolve;
        }),
    );
    const wrapper = await mountView("?task_id=task-1");
    const cancelButton = wrapper.findAll("button").find((button) => button.text() === "取消");
    await cancelButton?.trigger("click");

    expect(cancelButton?.attributes("disabled")).toBeDefined();
    resolveCancel({ ...task, status: "cancelled", available_actions: ["rerun"] });
    await flushPromises();
    expect(taskApi.cancelTask).toHaveBeenCalledTimes(1);
  });

  it("shows a safe network error without hard-coded task rows", async () => {
    vi.mocked(taskApi.listTasks).mockRejectedValueOnce(new Error("offline"));
    const wrapper = await mountView();

    expect(wrapper.text()).toContain("任务中心加载失败");
    expect(wrapper.text()).not.toContain("synthetic-product");
  });

  it.each([
    [409, "任务状态已变化，请刷新"],
    [404, "资源不存在或无权访问"],
    [422, "安全校验失败"],
  ])("maps HTTP %s detail failures to safe feedback", async (status, message) => {
    vi.mocked(taskApi.getTask).mockRejectedValueOnce(
      new FrontendApiError({
        code: "TEST_ERROR",
        message: status === 422 ? "安全校验失败" : "request failed",
        status,
      }),
    );
    const wrapper = await mountView("?task_id=task-1");
    expect(wrapper.text()).toContain(message);
  });

  it("registers /tasks with the real Task Center component", async () => {
    const record = applicationRouter.getRoutes().find((route) => route.path === "/tasks");
    expect(record).toBeDefined();
    const loader = record?.components?.default;
    expect(typeof loader).toBe("function");
    const loaded = await (loader as () => Promise<{ default: typeof TaskCenterView }>)();
    expect(loaded.default).toBe(TaskCenterView);
  });
});
