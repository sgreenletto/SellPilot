import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FrontendApiError } from "@/api/http";
import ReviewAnalysisView from "@/views/reviews/ReviewAnalysisView.vue";

const api = vi.hoisted(() => ({
  listProductReviews: vi.fn(),
  createReviewAnalysis: vi.fn(),
  runReviewAnalysis: vi.fn(),
  listReviewEvidence: vi.fn(),
}));
vi.mock("@/api/review-analysis", () => api);
vi.mock("@/components/charts/ReviewTrendChart.vue", () => ({
  default: { template: '<div aria-label="评论时间趋势图"></div>' },
}));

const review = {
  review_id: "REV1",
  product_id: "PROD0001",
  site: "sg",
  rating: 2,
  content: "Packaging damaged",
  translated_content: null,
  language: "English",
  sentiment_hint: "negative",
  issue_type: "packaging",
  created_at: "2026-01-01T00:00:00Z",
  source_type: "simulated_experiment",
  is_mock_data: true,
};
const result = {
  analysis_id: "A1",
  agent_task_id: "T1",
  product_id: "PROD0001",
  site: "sg",
  status: "SUCCEEDED",
  progress: 100,
  current_step: null,
  steps: [{ step_name: "load_reviews", status: "SUCCEEDED", error_message: null }],
  analyzer_version: "review-analysis-v1.0.0",
  analysis_mode: "rule",
  prompt_version: null,
  model_version: null,
  quality: { included_count: 1 },
  sentiment: { positive: 0, neutral: 0, negative: 1 },
  topics: [{ topic: "packaging", count: 1, frequency_rate: "1", negative_count: 1, severity: "1" }],
  pain_points: [
    {
      pain_point: "packaging",
      negative_count: 1,
      frequency_rate: "1",
      severity: "1",
      affected_sites: ["sg"],
    },
  ],
  keywords: [],
  trends: [],
  judgements: [],
  error_message: null,
  is_mock_data: true,
  started_at: null,
  finished_at: null,
};

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/market/reviews", component: ReviewAnalysisView }],
  });
  await router.push("/market/reviews");
  await router.isReady();
  return mount(ReviewAnalysisView, { global: { plugins: [router] } });
}

describe("ReviewAnalysisView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listProductReviews.mockResolvedValue([review]);
    api.createReviewAnalysis.mockResolvedValue({ analysis_id: "A1" });
    api.runReviewAnalysis.mockResolvedValue(result);
    api.listReviewEvidence.mockResolvedValue({
      items: [
        {
          id: "E1",
          review_id: "REV1",
          label: "packaging",
          confidence: "0.9",
          original_content: review.content,
          translated_content: null,
        },
      ],
      page: 1,
      page_size: 20,
      total: 1,
    });
  });

  it("filters reviews and renders explicit translation state", async () => {
    const wrapper = await mountView();
    await flushPromises();
    expect(wrapper.text()).toContain("Packaging damaged");
    expect(wrapper.text()).toContain("当前仅展示数据源已有译文");
    expect(api.listProductReviews).toHaveBeenCalledOnce();
  });

  it("runs analysis and locates representative evidence", async () => {
    const wrapper = await mountView();
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("运行分析"))
      ?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("情感分布");
    expect(wrapper.text()).toContain("规则分析");
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("定位评论"))
      ?.trigger("click");
    expect(wrapper.get("#review-REV1").classes()).toContain("selected");
  });

  it("shows backend disconnected and empty states honestly", async () => {
    api.listProductReviews.mockRejectedValue(
      new FrontendApiError({
        code: "NETWORK_ERROR",
        message: "后端未连接",
        status: 0,
      }),
    );
    const wrapper = await mountView();
    await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).toContain("后端未连接");
    expect(wrapper.text()).toContain("后端未连接，无法加载评论");
  });

  it("supports review pagination and live evidence filtering", async () => {
    api.listProductReviews.mockResolvedValue(
      Array.from({ length: 20 }, (_, index) => ({
        ...review,
        review_id: `REV${index}`,
      })),
    );
    const wrapper = await mountView();
    await flushPromises();
    const next = wrapper.findAll("button").find((button) => button.text() === "下一页");
    await next?.trigger("click");
    await flushPromises();
    expect(api.listProductReviews.mock.calls.at(-1)?.[0]).toMatchObject({ offset: 20, limit: 20 });

    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("运行分析"))
      ?.trigger("click");
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("packaging"))
      ?.trigger("click");
    await flushPromises();
    expect(api.listReviewEvidence).toHaveBeenLastCalledWith("A1", 1, "topic", "packaging");
    expect(wrapper.text()).toContain("load_reviews");
  });
});
