import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as assistantApi from "@/api/assistant";
import type { AssistantCapability, AssistantPlan, AssistantTaskResult } from "@/api/assistant";
import { FrontendApiError } from "@/api/http";
import { router as applicationRouter } from "@/router";
import AssistantView from "@/views/assistant/AssistantView.vue";
import type { TaskDetail } from "@/types/contracts";

vi.mock("@/api/assistant", () => ({
  createAssistantTask: vi.fn(),
  listAssistantCapabilities: vi.fn(),
  listRecentAssistantTasks: vi.fn(),
  planAssistantMessage: vi.fn(),
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
      summary: "Read order logistics through CommerceQueryService.",
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

const recentTask: TaskDetail = {
  id: taskResult.task_id,
  task_type: "platform_operation",
  workflow_name: "logistics_query",
  workflow_version: "1.0.0",
  parent_task_id: null,
  status: "succeeded",
  current_step: null,
  current_node: null,
  result: {},
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
  const wrapper = mount(AssistantView, { global: { plugins: [router] } });
  await flushPromises();
  return { wrapper, router };
}

async function submitMessage(
  wrapper: Awaited<ReturnType<typeof mountView>>["wrapper"],
  value: string,
) {
  await wrapper.get('[data-testid="assistant-message"]').setValue(value);
  const submit = wrapper.findAll("button").find((button) => button.text().includes("生成计划"));
  await submit?.trigger("click");
  await flushPromises();
}

describe("AssistantView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assistantApi.listAssistantCapabilities).mockResolvedValue(capabilities);
    vi.mocked(assistantApi.listRecentAssistantTasks).mockResolvedValue([]);
    vi.mocked(assistantApi.planAssistantMessage).mockResolvedValue(availablePlan);
    vi.mocked(assistantApi.createAssistantTask).mockResolvedValue(taskResult);
  });

  it("loads server capabilities and renders the Mock plan contract", async () => {
    const { wrapper } = await mountView();

    expect(assistantApi.listAssistantCapabilities).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("物流查询");
    expect(wrapper.text()).toContain("知识库检索");
    expect(wrapper.text()).toContain("Mock 模式");
    expect(wrapper.text()).toContain("仅契约");
  });

  it("plan mode renders the plan without inventing a Task ID", async () => {
    const { wrapper } = await mountView();
    await submitMessage(wrapper, "查询订单 ORD000001 的物流");

    expect(assistantApi.planAssistantMessage).toHaveBeenCalledWith("查询订单 ORD000001 的物流");
    expect(wrapper.get('[data-testid="assistant-plan"]').text()).toContain("logistics_query");
    expect(wrapper.text()).toContain("ORD000001");
    expect(wrapper.text()).toContain("get_order_logistics");
    expect(wrapper.text()).toContain("只读计划");
    expect(wrapper.text()).toContain("创建任务");
    expect(wrapper.text()).not.toContain(taskResult.task_id);
    expect(wrapper.text()).not.toContain("执行成功");
  });

  it("shows missing parameters and unavailable reasons without pretending to execute", async () => {
    vi.mocked(assistantApi.planAssistantMessage).mockResolvedValueOnce({
      ...availablePlan,
      detected_intent: "knowledge_query",
      extracted_parameters: {},
      missing_parameters: ["query"],
      selected_capability: "knowledge_query",
      tool_names: [],
      steps: [],
      availability: "contract_only",
      unavailable_reason: "RAG 尚未接入统一 ToolRegistry/WorkflowRegistry。",
      can_execute: false,
      target_path: "/customer-service/knowledge",
    });
    const { wrapper } = await mountView();
    await submitMessage(wrapper, "查询知识库");

    expect(wrapper.text()).toContain("query");
    expect(wrapper.text()).toContain("RAG 尚未接入统一 ToolRegistry/WorkflowRegistry");
    expect(wrapper.text()).toContain("不会创建 Task");
    expect(wrapper.find('[data-testid="assistant-execution-actions"]').exists()).toBe(false);
  });

  it("creates and runs an available capability, then links to the exact Task Center ID", async () => {
    const { wrapper, router } = await mountView();
    await submitMessage(wrapper, "查询订单 ORD000001 的物流");
    const run = wrapper.findAll("button").find((button) => button.text().includes("创建并运行"));

    await run?.trigger("click");
    await flushPromises();

    expect(assistantApi.createAssistantTask).toHaveBeenCalledWith(
      "查询订单 ORD000001 的物流",
      "create_and_run",
    );
    expect(wrapper.get('[data-testid="assistant-task-result"]').text()).toContain(
      taskResult.task_id,
    );
    const taskCenter = wrapper
      .findAll("button")
      .find((button) => button.text().includes("前往 Task Center"));
    await taskCenter?.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.path).toBe("/tasks");
    expect(router.currentRoute.value.query.task_id).toBe(taskResult.task_id);
  });

  it("disables execution and shows concrete missing fields for available plans", async () => {
    vi.mocked(assistantApi.planAssistantMessage).mockResolvedValueOnce({
      ...availablePlan,
      extracted_parameters: {},
      missing_parameters: ["order_id"],
      can_execute: false,
    });
    const { wrapper } = await mountView();
    await submitMessage(wrapper, "查询物流");

    expect(wrapper.text()).toContain("order_id");
    const actions = wrapper.get('[data-testid="assistant-execution-actions"]');
    expect(
      actions.findAll("button").every((button) => button.attributes("disabled") !== undefined),
    ).toBe(true);
  });

  it("loads recent Assistant tasks and opens their query-linked detail", async () => {
    vi.mocked(assistantApi.listRecentAssistantTasks).mockResolvedValueOnce([recentTask]);
    const { wrapper, router } = await mountView();

    expect(wrapper.text()).toContain("最近 Assistant 任务");
    expect(wrapper.text()).toContain(recentTask.id);
    const view = wrapper.findAll("button").find((button) => button.text() === "查看");
    await view?.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.task_id).toBe(recentTask.id);
  });

  it("shows safe API errors", async () => {
    vi.mocked(assistantApi.planAssistantMessage).mockRejectedValueOnce(
      new FrontendApiError({
        code: "PARAMETER_ERROR",
        message: "Invalid request parameters",
        status: 422,
      }),
    );
    const { wrapper } = await mountView();
    await submitMessage(wrapper, "查询物流");

    expect(wrapper.get('[role="alert"]').text()).toContain("输入参数不符合 Assistant 契约");
  });

  it.each([
    [401, "登录状态已失效"],
    [409, "请求冲突"],
    [422, "输入参数不符合 Assistant 契约"],
    [500, "服务暂时不可用"],
  ])("renders execution error status %i safely", async (status, expected) => {
    vi.mocked(assistantApi.createAssistantTask).mockRejectedValueOnce(
      new FrontendApiError({
        code: "APP_ERROR",
        message: "synthetic error",
        status,
      }),
    );
    const { wrapper } = await mountView();
    await submitMessage(wrapper, "查询订单 ORD000001 的物流");
    const create = wrapper.findAll("button").find((button) => button.text() === "创建任务");
    await create?.trigger("click");
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toContain(expected);
  });

  it("routes /assistant to the real plan view instead of the placeholder", () => {
    const route = applicationRouter.getRoutes().find((item) => item.path === "/assistant");
    const component = route?.components?.default;

    expect(route?.name).toBe("assistant");
    expect(String(component)).toContain("AssistantView.vue");
    expect(String(component)).not.toContain("ModulePlaceholderView");
  });
});
