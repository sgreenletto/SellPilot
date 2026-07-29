import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as assistantApi from "@/api/assistant";
import type { AssistantCapability, AssistantPlan } from "@/api/assistant";
import { FrontendApiError } from "@/api/http";
import { router as applicationRouter } from "@/router";
import AssistantView from "@/views/assistant/AssistantView.vue";

vi.mock("@/api/assistant", () => ({
  listAssistantCapabilities: vi.fn(),
  planAssistantMessage: vi.fn(),
}));

const capabilities: AssistantCapability[] = [
  {
    capability_key: "logistics_query",
    display_name: "物流查询",
    intent: "logistics_query",
    workflow_name: null,
    workflow_version: null,
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
  selected_workflow: null,
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

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/assistant", component: AssistantView },
      { path: "/orders", component: { template: "<div>orders</div>" } },
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
    vi.mocked(assistantApi.planAssistantMessage).mockResolvedValue(availablePlan);
  });

  it("loads server capabilities and renders the Mock plan contract", async () => {
    const { wrapper } = await mountView();

    expect(assistantApi.listAssistantCapabilities).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("物流查询");
    expect(wrapper.text()).toContain("知识库检索");
    expect(wrapper.text()).toContain("Mock 模式");
    expect(wrapper.text()).toContain("仅契约");
  });

  it("requests a plan and renders intent, parameters, tools, risk, and next-stage status", async () => {
    const { wrapper } = await mountView();
    await submitMessage(wrapper, "查询订单 ORD000001 的物流");

    expect(assistantApi.planAssistantMessage).toHaveBeenCalledWith("查询订单 ORD000001 的物流");
    expect(wrapper.get('[data-testid="assistant-plan"]').text()).toContain("logistics_query");
    expect(wrapper.text()).toContain("ORD000001");
    expect(wrapper.text()).toContain("get_order_logistics");
    expect(wrapper.text()).toContain("只读计划");
    expect(wrapper.text()).toContain("下一阶段将接入统一 Task 执行");
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
    expect(wrapper.text()).toContain("不会自动运行 contract_only");
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

    expect(wrapper.get('[role="alert"]').text()).toContain("输入参数不符合计划契约");
  });

  it("routes /assistant to the real plan view instead of the placeholder", () => {
    const route = applicationRouter.getRoutes().find((item) => item.path === "/assistant");
    const component = route?.components?.default;

    expect(route?.name).toBe("assistant");
    expect(String(component)).toContain("AssistantView.vue");
    expect(String(component)).not.toContain("ModulePlaceholderView");
  });
});
