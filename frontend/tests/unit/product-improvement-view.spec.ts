import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FrontendApiError } from "@/api/http";
import ProductImprovementView from "@/views/reviews/ProductImprovementView.vue";

const api = vi.hoisted(() => ({
  generateImprovementReport: vi.fn(),
  updateImprovementSuggestion: vi.fn(),
  exportImprovementReport: vi.fn(),
  listImprovementDrafts: vi.fn(),
  requestImprovementDraft: vi.fn(),
  requestImprovementDraftHistoryClear: vi.fn(),
  requestImprovementDraftRevision: vi.fn(),
  confirmImprovementDraft: vi.fn(),
  cancelImprovementDraft: vi.fn(),
}));
const reviewApi = vi.hoisted(() => ({
  listReviewEvidence: vi.fn(),
}));
vi.mock("@/api/product-improvement", () => api);
vi.mock("@/api/review-analysis", () => reviewApi);

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
  input_conditions: { site: "id" },
  summary: { sample_size: 10, suggestion_count: 1, limitations: ["Mock 数据"] },
  created_at: "2026-07-28T00:00:00Z",
  suggestions: [suggestion],
};

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/market/reviews/improvement", component: ProductImprovementView },
      { path: "/market/reviews", component: { template: "<div>reviews</div>" } },
      { path: "/tasks", component: { template: "<div>tasks</div>" } },
    ],
  });
  await router.push("/market/reviews/improvement?analysis_id=A1&regenerate=entry-1");
  await router.isReady();
  return mount(ProductImprovementView, { global: { plugins: [router] } });
}

describe("ProductImprovementView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.generateImprovementReport.mockResolvedValue(structuredClone(report));
    api.listImprovementDrafts.mockResolvedValue({ items: [], total: 0 });
    reviewApi.listReviewEvidence.mockResolvedValue({
      items: [
        {
          id: "E1",
          review_id: "REV1",
          language: "en",
          rating: 2,
          evidence_type: "topic",
          label: "packaging",
          sentiment: "negative",
          issue_type: "packaging",
          original_content: "The outer box arrived crushed.",
          translated_content: "收到时外包装已经被压坏。",
          source_created_at: "2026-07-28T00:00:00Z",
          confidence: "0.9",
          is_mock_data: true,
        },
        {
          id: "E2",
          review_id: "REV2",
          language: "en",
          rating: 2,
          evidence_type: "topic",
          label: "packaging",
          sentiment: "negative",
          issue_type: "packaging",
          original_content: "Packaging protection was insufficient.",
          translated_content: "包装防护不足。",
          source_created_at: "2026-07-28T00:00:00Z",
          confidence: "0.9",
          is_mock_data: true,
        },
      ],
      page: 1,
      page_size: 100,
      total: 2,
    });
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
    api.requestImprovementDraftRevision.mockResolvedValue({
      id: "C2",
      operation_type: "product_improvement.revise_content_draft",
      status: "PENDING",
      risk_warning: "确认后新增版本。",
      execution_result: null,
    });
    api.requestImprovementDraftHistoryClear.mockResolvedValue({
      id: "C3",
      operation_type: "product_improvement.clear_draft_history",
      status: "PENDING",
      risk_warning: "确认后清空页面历史。",
      execution_result: null,
    });
    api.confirmImprovementDraft.mockResolvedValue({
      id: "C1",
      status: "CONFIRMED",
      risk_warning: "确认后仅创建 Mock 草稿。",
      execution_result: { status: "DRAFT", content_id: "CONTENT1", version_id: "VERSION1" },
    });
  });

  it("loads the linked analysis and requires acceptance before draft selection", async () => {
    const wrapper = await mountView();
    await flushPromises();
    expect(api.generateImprovementReport).toHaveBeenCalledWith("A1", true);

    expect(wrapper.text()).toContain("问题频率20%");
    expect(wrapper.text()).toContain("严重程度80%");
    expect(wrapper.text()).toContain("结论置信度90%");
    expect(wrapper.text()).toContain("证据评论2 条");
    expect(wrapper.text()).toContain("查看 2 条证据评论");
    await wrapper.get(".evidence-reviews summary").trigger("click");
    expect(wrapper.text()).toContain("The outer box arrived crushed.");
    expect(wrapper.text()).toContain("译文：收到时外包装已经被压坏。");
    expect(wrapper.text()).not.toContain("REV1");
    expect(wrapper.text()).toContain("导出工厂改良报告");
    const draftButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("创建改良商品草稿"));
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
      .find((button) => button.text().includes("创建改良商品草稿"))
      ?.trigger("click");
    await flushPromises();

    expect(api.requestImprovementDraft).toHaveBeenCalledWith(
      "R1",
      ["S1"],
      expect.stringMatching(/^improvement-R1-/),
      "id",
    );
    expect(wrapper.text()).toContain("确认前不会创建草稿");
    const confirmButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("确认创建草稿"));
    expect(confirmButton).toBeDefined();
    expect(wrapper.get(".confirmation").text()).toContain("等待确认");
    expect(wrapper.get(".confirmation").text()).not.toContain("pending");
    expect(wrapper.text()).not.toContain("前往任务中心");

    await confirmButton?.trigger("click");
    await flushPromises();
    expect(api.confirmImprovementDraft).toHaveBeenCalledWith("C1");
    expect(wrapper.text()).toContain("未发布商品");
    expect(wrapper.text()).toContain("草稿已保存为产品改良的待编辑版本");
    expect(wrapper.text()).toContain("任务中心仅保留本次操作记录");
    expect(wrapper.text()).not.toContain("可前往任务中心查看");
    const collapseDraftButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("收起改良草稿"));
    expect(collapseDraftButton).toBeDefined();
    expect(wrapper.get(".draft-preview").text()).toContain("PROD0001 产品改良方案");
    expect(wrapper.get(".draft-preview").text()).toContain("改进包装");
    expect(wrapper.get(".draft-preview").text()).toContain("增加运输防护");
    expect(wrapper.get(".draft-preview").text()).toContain("不是已发布的商品文案");
  });

  it("always provides a return entry to review analysis", async () => {
    const wrapper = await mountView();
    await flushPromises();
    const backButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("返回评论分析"));
    expect(backButton).toBeDefined();
    await backButton?.trigger("click");
    await flushPromises();
    expect(wrapper.vm.$router.currentRoute.value.path).toBe("/market/reviews");
  });

  it("loads and edits the latest improvement draft through a confirmation", async () => {
    api.listImprovementDrafts.mockResolvedValue({
      items: [
        {
          id: "VERSION1",
          content_id: "CONTENT1",
          source_product_id: "PROD0001",
          site: "id",
          version: 1,
          sequence: 4,
          status: "DRAFT",
          report_id: "R1",
          items: [{ title: "改进包装", description: "增加运输防护。" }],
          change_summary: "基于已采纳评论改良建议创建",
          created_at: "2026-07-29T00:00:00Z",
        },
      ],
      total: 1,
    });
    const wrapper = await mountView();
    await flushPromises();

    expect(wrapper.text()).toContain("产品改良草稿历史");
    expect(wrapper.text()).toContain("v4");
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("编辑最新草稿"))
      ?.trigger("click");
    const textarea = wrapper.get(".draft-editor textarea");
    await textarea.setValue("增加缓冲材料并执行跌落测试。");
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("申请保存新版本"))
      ?.trigger("click");
    await flushPromises();

    expect(api.requestImprovementDraftRevision).toHaveBeenCalledWith(
      "VERSION1",
      1,
      [{ title: "改进包装", description: "增加缓冲材料并执行跌落测试。" }],
      expect.stringMatching(/^improvement-revision-VERSION1-/),
    );
    expect(wrapper.text()).toContain("确认保存新版本");
  });

  it("requires confirmation before clearing the current product draft history", async () => {
    api.listImprovementDrafts.mockResolvedValue({
      items: [
        {
          id: "VERSION4",
          content_id: "CONTENT1",
          source_product_id: "PROD0001",
          site: "id",
          version: 8,
          sequence: 4,
          status: "DRAFT",
          report_id: "R1",
          items: [{ title: "改进包装", description: "增加运输防护。" }],
          change_summary: "人工编辑",
          created_at: "2026-07-29T00:00:00Z",
        },
      ],
      total: 1,
    });
    const wrapper = await mountView();
    await flushPromises();

    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("清空草稿历史"))
      ?.trigger("click");
    await flushPromises();

    expect(api.requestImprovementDraftHistoryClear).toHaveBeenCalledWith(
      "PROD0001",
      expect.stringMatching(/^improvement-clear-PROD0001-/),
    );
    expect(wrapper.text()).toContain("确认清空历史");
    expect(wrapper.text()).toContain("新草稿将从 v1 重新编号");
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
