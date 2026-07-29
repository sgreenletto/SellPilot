import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FrontendApiError } from "@/api/http";
import SelectionWorkbenchView from "@/views/selection/SelectionWorkbenchView.vue";

const selectionApi = vi.hoisted(() => ({
  listSelectionCandidates: vi.fn(),
  createSelectionAnalysis: vi.fn(),
  compareSelectionProducts: vi.fn(),
  exportSelectionAnalysis: vi.fn(),
  downloadSelectionExport: vi.fn(),
}));

vi.mock("@/api/selection", () => selectionApi);

const candidate = {
  product_id: "P001",
  title: "Mock Wireless Earbuds",
  category_id: "CAT-001",
  category_name: "Electronics",
  site: "sg",
  currency: "SGD",
  price: "50.00",
  cost: "20.00",
  shipping_cost: "5.00",
  sales_count: 120,
  rating: "4.50",
  review_count: 20,
  search_index: "80",
  sales_index: "75",
  competition_index: "30",
  growth_rate: "0.1",
  source_name: "simulated_experiment",
  is_mock_data: true,
};

const result = {
  id: "R001",
  product_id: "P001",
  title: candidate.title,
  rank: 1,
  total_score: "82.1000",
  data_completeness: "0.7500",
  currency: "SGD",
  site: "sg",
  profit: { profit: "20.00", margin: "0.4000" },
  metrics: {
    demand: {
      score: "90.0000",
      configured_weight: "0.25",
      effective_weight: "0.25",
      inputs: { sales_count: 120 },
      formula: "normalized demand",
    },
  },
  explanation: {
    summary: "需求与利润表现良好",
    evidence: [{ metric: "total_score", value: "82.1000", source: "selection-v1.0.0" }],
    risks: [],
    generation_mode: "rule_template",
  },
  risk_warnings: ["logistics data missing"],
  evidence: {},
  is_mock_data: true,
};
const secondResult = {
  ...result,
  id: "R002",
  product_id: "P002",
  title: "Mock Portable Speaker",
  rank: 2,
  total_score: "76.5000",
};

async function mountWorkbench() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/market/selection", component: SelectionWorkbenchView }],
  });
  await router.push("/market/selection");
  await router.isReady();
  return mount(SelectionWorkbenchView, { global: { plugins: [router] } });
}

describe("SelectionWorkbenchView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    selectionApi.listSelectionCandidates.mockResolvedValue([candidate]);
    selectionApi.createSelectionAnalysis.mockResolvedValue({
      task_id: "task-1",
      agent_task_id: "agent-1",
      status: "SUCCEEDED",
      formula_version: "selection-v1.0.0",
      generation_mode: "rule_template",
      total_candidates: 1,
      ranked_count: 1,
      excluded_count: 0,
      results: [result, secondResult],
      excluded: [],
      is_mock_data: true,
    });
    selectionApi.compareSelectionProducts.mockResolvedValue([result, secondResult]);
    selectionApi.exportSelectionAnalysis.mockResolvedValue({
      filename: "selection-task-1.json",
      content_type: "application/json",
      checksum_sha256: "a".repeat(64),
      task: {
        task_id: "task-1",
        agent_task_id: "agent-1",
        status: "SUCCEEDED",
        criteria: {},
        formula_version: "selection-v1.0.0",
        is_mock_data: true,
        results: [result, secondResult],
      },
    });
    selectionApi.downloadSelectionExport.mockReturnValue("selection-task-1.md");
  });

  it("loads formal candidates and renders explainable results", async () => {
    const wrapper = await mountWorkbench();
    await flushPromises();

    expect(wrapper.text()).toContain("Mock Wireless Earbuds");
    expect(wrapper.text()).toContain("Shopee 模拟实验数据");

    const analyze = wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析全部候选"));
    await analyze?.trigger("click");
    await flushPromises();

    expect(selectionApi.createSelectionAnalysis).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("商品机会总分 82.1");
    expect(wrapper.text()).toContain("规则解释");
    expect(wrapper.find(".risk-list").exists()).toBe(false);
  });

  it("shows an explicit backend disconnected state", async () => {
    selectionApi.listSelectionCandidates.mockRejectedValue(
      new FrontendApiError({
        code: "NETWORK_ERROR",
        message: "后端未连接",
        status: 0,
      }),
    );

    const wrapper = await mountWorkbench();
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toContain("后端未连接");
    expect(wrapper.text()).toContain("没有可分析的候选商品");
  });

  it("distinguishes a request timeout from a disconnected backend", async () => {
    selectionApi.listSelectionCandidates.mockRejectedValue(
      new FrontendApiError({
        code: "NETWORK_ERROR",
        message: "请求超时",
        status: 0,
      }),
    );

    const wrapper = await mountWorkbench();
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toContain("候选请求超时");
    expect(wrapper.get('[role="alert"]').text()).not.toContain("后端未连接");
  });

  it("identifies a batch analysis timeout separately from candidate loading", async () => {
    selectionApi.createSelectionAnalysis.mockRejectedValue(
      new FrontendApiError({
        code: "NETWORK_ERROR",
        message: "请求超时",
        status: 0,
      }),
    );
    const wrapper = await mountWorkbench();
    await flushPromises();

    const analyze = wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析全部候选"));
    await analyze?.trigger("click");
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toContain("选品分析超时");
    expect(wrapper.get('[role="alert"]').text()).not.toContain("候选请求超时");
  });

  it("blocks analysis when the price range is invalid", async () => {
    const wrapper = await mountWorkbench();
    await flushPromises();
    const inputs = wrapper.findAll("input");
    const minPrice = inputs.find(
      (input) =>
        input.attributes("placeholder") === "0" &&
        input.element.closest("label")?.textContent?.includes("最低价格"),
    );
    const maxPrice = inputs.find((input) => input.attributes("placeholder") === "不限");
    await minPrice?.setValue("100");
    await maxPrice?.setValue("50");
    await flushPromises();

    expect(wrapper.text()).toContain("最高价格不能低于最低价格");
    const analyze = wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析全部候选"));
    expect(analyze?.attributes("disabled")).toBeDefined();
  });

  it("supports two-product comparison and report export", async () => {
    const wrapper = await mountWorkbench();
    await flushPromises();
    const analyze = wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析全部候选"));
    await analyze?.trigger("click");
    await flushPromises();

    const compareCheckboxes = wrapper.findAll(".compare-check input");
    await compareCheckboxes[0]?.setValue(true);
    await compareCheckboxes[1]?.setValue(true);
    const compareButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("对比所选"));
    await compareButton?.trigger("click");
    await flushPromises();

    expect(selectionApi.compareSelectionProducts).toHaveBeenCalledWith("task-1", ["P001", "P002"]);
    expect(wrapper.text()).toContain("Mock Portable Speaker");

    const exportButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("导出报告"));
    await exportButton?.trigger("click");
    await flushPromises();
    expect(selectionApi.downloadSelectionExport).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("selection-task-1.md");
  });

  it("explains an analysis with no ranked products", async () => {
    selectionApi.createSelectionAnalysis.mockResolvedValue({
      task_id: "task-empty",
      agent_task_id: "agent-empty",
      status: "SUCCEEDED",
      formula_version: "selection-v1.0.0",
      generation_mode: "rule_template",
      total_candidates: 1,
      ranked_count: 0,
      excluded_count: 1,
      results: [],
      excluded: [{ product_id: "P001", reason: "minimum_profit" }],
      is_mock_data: true,
    });

    const wrapper = await mountWorkbench();
    await flushPromises();
    const analyze = wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析全部候选"));
    await analyze?.trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("没有商品满足利润条件");
    expect(wrapper.text()).toContain("1 个候选已被最低利润或利润率条件排除");
  });

  it("renders a schema-validated model explanation when available", async () => {
    selectionApi.createSelectionAnalysis.mockResolvedValue({
      task_id: "task-ai",
      agent_task_id: "agent-ai",
      status: "SUCCEEDED",
      formula_version: "selection-v1.0.0",
      generation_mode: "validated_generator",
      total_candidates: 1,
      ranked_count: 1,
      excluded_count: 0,
      results: [
        {
          ...result,
          explanation: {
            ...result.explanation,
            summary: "该商品需求稳定，利润空间具有竞争力。",
            generation_mode: "validated_generator",
          },
        },
      ],
      excluded: [],
      is_mock_data: true,
    });

    const wrapper = await mountWorkbench();
    await flushPromises();
    const analyze = wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析全部候选"));
    await analyze?.trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("校验生成解释");
    expect(wrapper.text()).toContain("该商品需求稳定，利润空间具有竞争力。");
  });

  it("closes the product detail with Escape", async () => {
    const wrapper = await mountWorkbench();
    await flushPromises();
    const analyze = wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析全部候选"));
    await analyze?.trigger("click");
    await flushPromises();

    const detailsButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("查看详情"));
    await detailsButton?.trigger("click");
    expect(wrapper.find('[aria-label="选品详情"]').exists()).toBe(true);

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[aria-label="选品详情"]').exists()).toBe(false);
  });
});
