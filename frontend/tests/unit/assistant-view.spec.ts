import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as assistantApi from "@/api/assistant";
import { FrontendApiError } from "@/api/http";
import * as taskApi from "@/api/tasks";
import { router as applicationRouter } from "@/router";
import type { AssistantCapability, AssistantPlan, AssistantTaskResult } from "@/api/assistant";
import type { TaskDetail, TaskStepDetail } from "@/types/contracts";
import AssistantView from "@/views/assistant/AssistantView.vue";

vi.mock("@/api/assistant", () => ({
  createAssistantTask: vi.fn(),
  listAssistantCapabilities: vi.fn(),
  listRecentAssistantTasks: vi.fn(),
  planAssistantMessage: vi.fn(),
}));

vi.mock("@/api/tasks", () => ({
  getTask: vi.fn(),
  listTaskSteps: vi.fn(),
  listTaskToolCalls: vi.fn(),
}));

const capabilities: AssistantCapability[] = [
  {
    capability_key: "logistics_query",
    display_name: "物流查询",
    intent: "logistics_query",
    workflow_name: "logistics_query",
    workflow_version: "1.0.0",
    required_parameters: ["order_id"],
    optional_parameters: [],
    tool_names: ["get_order_logistics"],
    risk_level: "read",
    requires_confirmation: false,
    availability: "available",
    unavailable_reason: null,
    example_message: "查询订单 ORD000001 的物流",
    target_path: "/orders",
  },
  {
    capability_key: "knowledge_query",
    display_name: "知识库检索",
    intent: "knowledge_query",
    workflow_name: null,
    workflow_version: null,
    required_parameters: ["query"],
    optional_parameters: ["category", "top_k"],
    tool_names: [],
    risk_level: "read",
    requires_confirmation: false,
    availability: "contract_only",
    unavailable_reason: "RAG 尚未接入统一 ToolRegistry/WorkflowRegistry。",
    example_message: "在知识库中检索退货政策",
    target_path: "/customer-service/knowledge",
  },
  {
    capability_key: "customer_service_reply",
    display_name: "客服回复建议",
    intent: "customer_service_reply",
    workflow_name: null,
    workflow_version: null,
    required_parameters: ["session_id"],
    optional_parameters: [],
    tool_names: [],
    risk_level: "read",
    requires_confirmation: false,
    availability: "unavailable",
    unavailable_reason: "客服工作流尚未开放。",
    example_message: "帮我回复买家的退款投诉",
    target_path: "/customer-service/conversations",
  },
];

const availablePlan: AssistantPlan = {
  detected_intent: "logistics_query",
  extracted_parameters: { order_id: "ORD000001" },
  missing_parameters: [],
  selected_capability: "logistics_query",
  selected_workflow: { name: "logistics_query", version: "1.0.0" },
  tool_names: ["get_order_logistics"],
  steps: [
    {
      order: 1,
      kind: "tool",
      name: "get_order_logistics",
      summary: "Read order logistics and tracks through CommerceQueryService.",
    },
  ],
  risk_summary: "只读计划；当前阶段不会执行工具或修改业务数据。",
  requires_confirmation: false,
  availability: "available",
  unavailable_reason: null,
  can_execute: true,
  target_path: "/orders",
  mock_mode: true,
  mock_notice: "当前为 Mock 计划模式：仅生成确定性执行计划，不创建任务。",
};

const taskResult: AssistantTaskResult = {
  detected_intent: "logistics_query",
  selected_capability: "logistics_query",
  workflow_name: "logistics_query",
  workflow_version: "1.0.0",
  plan: availablePlan,
  task_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  task_status: "succeeded",
  execution_mode: "create_and_run",
  confirmation_required: false,
  confirmation_id: null,
  duplicate: false,
  created_at: "2026-07-29T10:00:00Z",
};

const completedTask: TaskDetail = {
  id: taskResult.task_id,
  task_type: "platform_operation",
  workflow_name: "logistics_query",
  workflow_version: "1.0.0",
  parent_task_id: null,
  status: "succeeded",
  current_step: null,
  current_node: null,
  result: {
    logistics: {
      order_id: "ORD000001",
      tracking_number: "SPX000001",
      carrier: "SPX",
      status: "in_transit",
      latest_location: "新加坡分拨中心",
      tracks: [],
      is_mock_data: true,
    },
  },
  error_code: null,
  error_message: null,
  retry_count: 0,
  task_attempt: 1,
  request_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  created_by: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  created_at: "2026-07-29T10:00:00Z",
  started_at: "2026-07-29T10:00:01Z",
  finished_at: "2026-07-29T10:00:02Z",
  updated_at: "2026-07-29T10:00:02Z",
  completed_at: "2026-07-29T10:00:02Z",
  waiting_confirmation: false,
  waiting_reason: null,
  safe_error_summary: null,
  available_actions: ["rerun"],
};

const taskStep: TaskStepDetail = {
  id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
  task_id: taskResult.task_id,
  sequence: 1,
  node_name: "get_order_logistics",
  node_type: "tool",
  status: "succeeded",
  attempt_count: 1,
  input_summary: { order_id: "ORD000001" },
  output_summary: { status: "in_transit" },
  error_code: null,
  error_message: null,
  tool_call_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
  confirmation_id: null,
  metadata: null,
  started_at: "2026-07-29T10:00:01Z",
  completed_at: "2026-07-29T10:00:02Z",
};

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/assistant", component: AssistantView },
      { path: "/orders", component: { template: "<div>orders</div>" } },
      { path: "/tasks", component: { template: "<div>tasks</div>" } },
      {
        path: "/customer-service/knowledge",
        component: { template: "<div>knowledge</div>" },
      },
    ],
  });
  await router.push("/assistant");
  await router.isReady();
  const wrapper = mount(AssistantView, { global: { plugins: [router, createPinia()] } });
  await flushPromises();
  return { wrapper, router };
}

async function sendMessage(
  wrapper: Awaited<ReturnType<typeof mountView>>["wrapper"],
  value: string,
) {
  await wrapper.get('[data-testid="assistant-message"]').setValue(value);
  await wrapper.get('[data-testid="assistant-send"]').trigger("click");
  await flushPromises();
}

describe("AssistantView chat workspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(assistantApi.listAssistantCapabilities).mockResolvedValue(capabilities);
    vi.mocked(assistantApi.listRecentAssistantTasks).mockResolvedValue([]);
    vi.mocked(assistantApi.planAssistantMessage).mockResolvedValue(availablePlan);
    vi.mocked(assistantApi.createAssistantTask).mockResolvedValue(taskResult);
    vi.mocked(taskApi.getTask).mockResolvedValue(completedTask);
    vi.mocked(taskApi.listTaskSteps).mockResolvedValue([taskStep]);
    vi.mocked(taskApi.listTaskToolCalls).mockResolvedValue({
      items: [
        {
          id: taskStep.tool_call_id!,
          tool_name: "get_order_logistics",
          tool_version: "1.0.0",
          risk_level: "read",
          caller_type: "workflow",
          caller_name: "logistics_query",
          request_id: completedTask.request_id,
          user_id: completedTask.created_by,
          task_id: completedTask.id,
          task_step_id: taskStep.id,
          confirmation_id: null,
          input_summary: taskStep.input_summary,
          output_summary: taskStep.output_summary,
          attempt_history: null,
          status: "succeeded",
          attempt_count: 1,
          duration_ms: 12,
          error_code: null,
          error_message: null,
          started_at: taskStep.started_at!,
          completed_at: taskStep.completed_at,
          created_at: taskStep.started_at!,
        },
      ],
      page: 1,
      page_size: 100,
      total: 1,
      pages: 1,
    });
  });

  it("keeps the single page title in the global layout and removes duplicate foundation copy", async () => {
    const { wrapper } = await mountView();
    const route = applicationRouter.getRoutes().find((item) => item.path === "/assistant");

    expect(route?.meta.title).toBe("AI 运营助手");
    expect(wrapper.findAll("h1")).toHaveLength(0);
    expect(wrapper.text()).not.toContain("ASSISTANT FOUNDATION");
    expect(wrapper.text()).not.toContain("能力、Workflow 和风险均由服务端注册表决定");
    expect(wrapper.text()).toContain("你好，我可以协助查询订单");
  });

  it("plans first and runs an available request by default, then shows the real result", async () => {
    const { wrapper } = await mountView();
    await sendMessage(wrapper, "查询订单 ORD000001 的物流");

    expect(assistantApi.planAssistantMessage).toHaveBeenCalledWith("查询订单 ORD000001 的物流");
    expect(assistantApi.createAssistantTask).toHaveBeenCalledWith(
      "查询订单 ORD000001 的物流",
      "create_and_run",
      expect.any(String),
    );
    expect(taskApi.getTask).toHaveBeenCalledWith(taskResult.task_id);
    expect(wrapper.get(".chat-message--user").text()).toContain("查询订单 ORD000001 的物流");
    expect(wrapper.get('[data-testid="assistant-task-answer"]').text()).toContain("新加坡分拨中心");
    expect(wrapper.get('[data-testid="assistant-task-answer"]').text()).toContain("运输中");
  });

  it("asks for localized missing parameters without creating a task", async () => {
    vi.mocked(assistantApi.planAssistantMessage).mockResolvedValueOnce({
      ...availablePlan,
      extracted_parameters: {},
      missing_parameters: ["order_id"],
      can_execute: false,
    });
    const { wrapper } = await mountView();
    await sendMessage(wrapper, "查询订单物流");

    expect(assistantApi.createAssistantTask).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("请提供需要查询的订单编号");
    expect(wrapper.text()).not.toContain("missing_parameters");
  });

  it.each([
    [
      "contract_only" as const,
      "knowledge_query" as const,
      "该能力目前已完成接口契约，但尚未接入统一执行工作流",
    ],
    ["unavailable" as const, "customer_service_reply" as const, "该能力目前尚未开放执行"],
  ])(
    "does not execute %s capabilities and replies in Chinese",
    async (availability, intent, copy) => {
      vi.mocked(assistantApi.planAssistantMessage).mockResolvedValueOnce({
        ...availablePlan,
        detected_intent: intent,
        selected_capability: intent,
        selected_workflow: null,
        tool_names: [],
        steps: [],
        availability,
        unavailable_reason: "internal registry reason",
        can_execute: false,
      });
      const { wrapper } = await mountView();
      await sendMessage(wrapper, intent === "knowledge_query" ? "查询知识库" : "帮我回复买家");

      expect(assistantApi.createAssistantTask).not.toHaveBeenCalled();
      expect(wrapper.text()).toContain(copy);
      expect(wrapper.text()).not.toContain("internal registry reason");
    },
  );

  it("does not execute tools for an unknown request", async () => {
    vi.mocked(assistantApi.planAssistantMessage).mockResolvedValueOnce({
      ...availablePlan,
      detected_intent: "unknown",
      selected_capability: null,
      selected_workflow: null,
      tool_names: [],
      steps: [],
      availability: "unavailable",
      unavailable_reason: "unknown",
      can_execute: false,
    });
    const { wrapper } = await mountView();
    await sendMessage(wrapper, "今天天气怎么样");

    expect(assistantApi.createAssistantTask).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("暂时无法识别该请求，请换一种更具体的表达");
  });

  it("keeps plan details collapsed and localizes step copy while retaining internal IDs", async () => {
    const { wrapper } = await mountView();
    await sendMessage(wrapper, "查询订单 ORD000001 的物流");
    const details = wrapper.get('[data-testid="assistant-plan-details"]');

    expect(details.attributes("open")).toBeUndefined();
    expect(details.text()).toContain("查询订单物流");
    expect(details.text()).toContain("读取订单的物流信息");
    expect(details.text()).toContain("logistics_query@1.0.0");
    expect(details.text()).toContain("get_order_logistics");
  });

  it("shows only capability names in the collapsible quick-task panel and fills the composer", async () => {
    const { wrapper } = await mountView();
    const panel = wrapper.get('[data-testid="assistant-quick-tasks"]');
    const items = panel.findAll(".quick-task-item");

    expect(items.map((item) => item.text())).toEqual(["物流查询", "知识库检索", "客服回复建议"]);
    expect(panel.text()).not.toContain("查询订单 ORD000001 的物流");
    expect(panel.text()).not.toContain("仅契约");

    await items[0]?.trigger("click");
    expect(
      wrapper.get<HTMLTextAreaElement>('[data-testid="assistant-message"]').element.value,
    ).toBe("查询订单 ORD000001 的物流");

    await wrapper.get('[data-testid="assistant-quick-toggle"]').trigger("click");
    expect(wrapper.get(".assistant-workspace").classes()).toContain(
      "assistant-workspace--tasks-collapsed",
    );
    expect(panel.attributes("aria-hidden")).toBe("true");
    await wrapper.get('[data-testid="assistant-quick-toggle"]').trigger("click");
    expect(panel.attributes("aria-hidden")).toBe("false");
  });

  it("supports plan-only and create-only secondary modes without changing plan semantics", async () => {
    const { wrapper } = await mountView();
    const mode = wrapper.get<HTMLSelectElement>('[data-testid="assistant-mode"]');

    await mode.setValue("plan_only");
    await sendMessage(wrapper, "查询订单 ORD000001 的物流");
    expect(assistantApi.createAssistantTask).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("执行计划已生成，未创建任务或调用工具");

    await mode.setValue("create_only");
    await sendMessage(wrapper, "查询订单 ORD000001 的物流");
    expect(assistantApi.createAssistantTask).toHaveBeenLastCalledWith(
      "查询订单 ORD000001 的物流",
      "create_only",
      expect.any(String),
    );
    expect(wrapper.text()).toContain("任务已创建，尚未开始执行");
  });

  it("links to Task Center with the exact task id", async () => {
    const { wrapper, router } = await mountView();
    await sendMessage(wrapper, "查询订单 ORD000001 的物流");

    await wrapper.get('[data-testid="assistant-open-task"]').trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.path).toBe("/tasks");
    expect(router.currentRoute.value.query.task_id).toBe(taskResult.task_id);
  });

  it("shows the server safe failure reason, request id, and retry action", async () => {
    vi.mocked(taskApi.getTask).mockResolvedValueOnce({
      ...completedTask,
      status: "failed",
      result: null,
      error_code: "TASK_STATE_TOO_LARGE",
      error_message: "Workflow state exceeds the configured size limit",
      safe_error_summary: "Workflow state exceeds the configured size limit",
      available_actions: ["retry"],
    });
    const { wrapper } = await mountView();
    await sendMessage(wrapper, "分析新加坡站的选品机会");

    expect(wrapper.get('[role="alert"]').text()).toContain(
      "任务结果超过安全大小限制，请缩小查询范围后重试",
    );
    expect(wrapper.get('[role="alert"]').text()).toContain(completedTask.request_id);
    expect(wrapper.text()).not.toContain("Workflow state exceeds");
    expect(wrapper.get('[data-testid="assistant-retry"]').text()).toContain("重试");
  });

  it("sends on Enter, keeps Shift+Enter for a new line, and blocks duplicate submissions", async () => {
    let resolvePlan: ((value: AssistantPlan) => void) | undefined;
    vi.mocked(assistantApi.planAssistantMessage).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolvePlan = resolve;
        }),
    );
    const { wrapper } = await mountView();
    const input = wrapper.get<HTMLTextAreaElement>('[data-testid="assistant-message"]');
    await input.setValue("查询订单 ORD000001 的物流");
    await input.trigger("keydown", { key: "Enter", shiftKey: true });
    expect(assistantApi.planAssistantMessage).not.toHaveBeenCalled();

    await input.trigger("keydown", { key: "Enter" });
    expect(assistantApi.planAssistantMessage).toHaveBeenCalledOnce();
    expect(wrapper.get('[data-testid="assistant-send"]').attributes("disabled")).toBeDefined();
    await wrapper.get('[data-testid="assistant-send"]').trigger("click");
    expect(assistantApi.planAssistantMessage).toHaveBeenCalledOnce();

    resolvePlan?.(availablePlan);
    await flushPromises();
  });

  it.each([
    [401, "登录状态已失效"],
    [404, "任务或能力不存在"],
    [409, "请求冲突"],
    [422, "输入内容不符合助手要求"],
    [500, "服务暂时不可用"],
  ])("renders API status %i safely in the assistant reply", async (status, expected) => {
    vi.mocked(assistantApi.planAssistantMessage).mockRejectedValueOnce(
      new FrontendApiError({
        code: "APP_ERROR",
        message: "synthetic internal error",
        status,
      }),
    );
    const { wrapper } = await mountView();
    await sendMessage(wrapper, "查询物流");

    expect(wrapper.get('[role="alert"]').text()).toContain(expected);
    expect(wrapper.text()).not.toContain("synthetic internal error");
  });

  it("preserves server capability states without upgrading them in the UI", async () => {
    const { wrapper } = await mountView();
    const quickTasks = wrapper.get('[data-testid="assistant-quick-tasks"]');

    expect(quickTasks.find('[data-capability="knowledge_query"]').classes()).toContain(
      "quick-task-item--limited",
    );
    expect(quickTasks.find('[data-capability="customer_service_reply"]').classes()).toContain(
      "quick-task-item--limited",
    );
    expect(assistantApi.createAssistantTask).not.toHaveBeenCalled();
  });

  it("keeps the real Assistant route instead of the placeholder", () => {
    const route = applicationRouter.getRoutes().find((item) => item.path === "/assistant");
    const component = route?.components?.default;

    expect(route?.name).toBe("assistant");
    expect(String(component)).toContain("AssistantView.vue");
    expect(String(component)).not.toContain("ModulePlaceholderView");
  });
});
