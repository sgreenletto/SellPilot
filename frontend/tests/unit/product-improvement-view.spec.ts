import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FrontendApiError } from "@/api/http";
import ProductImprovementView from "@/views/reviews/ProductImprovementView.vue";

const api = vi.hoisted(() => ({
  generateImprovementReport: vi.fn(),
  updateImprovementSuggestion: vi.fn(),
  exportImprovementReport: vi.fn(),
  requestImprovementDraft: vi.fn(),
  confirmImprovementDraft: vi.fn(),
  cancelImprovementDraft: vi.fn(),
}));
vi.mock("@/api/product-improvement", () => api);

const suggestion = {
  id: "S1",
  suggestion_key: "packaging",
  category: "packaging",
  title: "改进包装",
  description: "增加运输防护。",
  priority: 1,
  severity: "0.8",
  confidence: "0.9",
  evidence_count: 2,
  frequency_rate: "0.2",
  evidence_review_ids: { items: ["REV1", "REV2"] },
  expected_impact: { limitations: "实施前人工核对。" },
  status: "PROPOSED",
};
const report = {
  id: "R1",
  review_analysis_result_id: "A1",
  source_product_id: "PROD0001",
  version: 1,
  algorithm_version: "product-improvement-rule-v1.0.0",
  status: "READY",
  source_type: "mock_shopee",
  is_mock_data: true,
  data_sources: {},
  input_conditions: {},
  summary: { sample_size: 10, suggestion_count: 1, limitations: ["Mock 数据"] },
  created_at: "2026-07-28T00:00:00Z",
  suggestions: [suggestion],
};

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/market/reviews/improvement", component: ProductImprovementView },
      { path: "/tasks", component: { template: "<div>tasks</div>" } },
    ],
  });
  await router.push("/market/reviews/improvement?analysis_id=A1");
  await router.isReady();
  return mount(ProductImprovementView, { global: { plugins: [router] } });
}

describe("ProductImprovementView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.generateImprovementReport.mockResolvedValue(structuredClone(report));
    api.updateImprovementSuggestion.mockImplementation(
      (_id: string, payload: Record<string, unknown>) => ({
        ...structuredClone(suggestion),
        ...payload,
      }),
    );
    api.requestImprovementDraft.mockResolvedValue({
      id: "C1",
      status: "PENDING",
      risk_warning: "确认后仅创建 Mock 草稿。",
      execution_result: null,
    });
    api.confirmImprovementDraft.mockResolvedValue({
      id: "C1",
      status: "CONFIRMED",
      risk_warning: "确认后仅创建 Mock 草稿。",
      execution_result: { status: "DRAFT" },
    });
  });

  it("loads the linked analysis and requires acceptance before draft selection", async () => {
    const wrapper = await mountView();
    await flushPromises();

    expect(api.generateImprovementReport).toHaveBeenCalledWith("A1");
    expect(wrapper.text()).toContain("问题频率20%");
    expect(wrapper.text()).toContain("严重程度80%");
    expect(wrapper.text()).toContain("结论置信度90%");
    expect(wrapper.text()).toContain("证据评论2 条");
    expect(wrapper.text()).toContain("查看 2 条证据评论编号");
    expect(wrapper.text()).toContain("导出工厂改良报告");
    const draftButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("提交草稿确认"));
    expect(draftButton?.attributes("disabled")).toBeDefined();

    await wrapper
      .findAll("button")
      .find((button) => button.text().trim() === "采纳")
      ?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("建议已采纳并加入草稿范围");
    expect(draftButton?.attributes("disabled")).toBeUndefined();
  });

  it("creates a pending task before explicit confirmation and accepts uppercase status", async () => {
    const wrapper = await mountView();
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text().trim() === "采纳")
      ?.trigger("click");
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("提交草稿确认"))
      ?.trigger("click");
    await flushPromises();

    expect(api.requestImprovementDraft).toHaveBeenCalledWith(
      "R1",
      ["S1"],
      expect.stringMatching(/^improvement-R1-/),
    );
    expect(wrapper.text()).toContain("尚未生成任何商品内容草稿");
    const confirmButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("确认创建草稿"));
    expect(confirmButton).toBeDefined();
    expect(wrapper.get(".confirmation").text()).toContain("等待确认");
    expect(wrapper.get(".confirmation").text()).not.toContain("pending");

    await confirmButton?.trigger("click");
    await flushPromises();
    expect(api.confirmImprovementDraft).toHaveBeenCalledWith("C1");
    expect(wrapper.text()).toContain("未发布商品");
  });

  it("shows API failures instead of leaving an unhandled action", async () => {
    api.updateImprovementSuggestion.mockRejectedValue(new Error("offline"));
    const wrapper = await mountView();
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text().trim() === "采纳")
      ?.trigger("click");
    await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).toContain("建议状态更新失败");
  });

  it("shows a compact retry state when AI generation times out", async () => {
    api.generateImprovementReport.mockRejectedValue(
      new FrontendApiError({
        code: "NETWORK_ERROR",
        message: "请求超时",
        status: 0,
      }),
    );
    const wrapper = await mountView();
    await flushPromises();
    expect(wrapper.get(".generator").text()).toContain("AI 生成等待时间过长，请稍后重试");
    expect(wrapper.get(".generator").text()).toContain("重新生成");
    expect(wrapper.text()).not.toContain("尚未生成改良报告");
  });

  it("explains why a report with no negative evidence has no suggestions", async () => {
    api.generateImprovementReport.mockResolvedValue({
      ...structuredClone(report),
      suggestions: [],
      summary: { sample_size: 5, suggestion_count: 0, limitations: ["规则分析"] },
    });
    const wrapper = await mountView();
    await flushPromises();
    expect(wrapper.text()).toContain("当前分析没有可生成的改良建议");
    expect(wrapper.text()).toContain("没有识别到具体改进信号");
    expect(wrapper.text()).toContain("调整评论范围后重新分析");
  });
});
