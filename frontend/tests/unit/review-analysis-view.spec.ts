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
  quality: {
    received_count: 1,
    included_count: 1,
    excluded_count: 0,
    flag_counts: {},
    excluded_review_ids: [],
  },
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
  keywords: [{ keyword: "packaging", count: 2, review_count: 1 }],
  trends: [],
  judgements: [],
  error_message: null,
  is_mock_data: true,
  started_at: null,
  finished_at: null,
};

async function mountView(path = "/market/reviews") {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/market/reviews", component: ReviewAnalysisView },
      { path: "/market/selection", component: { template: "<div>智能选品</div>" } },
    ],
  });
  await router.push(path);
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
          sentiment: "negative",
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
    expect(wrapper.text()).toContain("2 星 · 英语");
    expect(wrapper.text()).toContain("含改进信号");
    expect(wrapper.text()).toContain("包装");
    expect(wrapper.text()).not.toContain("negative");
    expect(api.listProductReviews).toHaveBeenCalledOnce();
  });

  it("loads the product and site passed from selection without starting analysis", async () => {
    const wrapper = await mountView("/market/reviews?source=selection&product_id=P009&site=id");
    await flushPromises();

    expect(wrapper.text()).toContain("已从智能选品带入商品");
    expect(wrapper.text()).toContain("P009 · ID");
    expect(wrapper.get('input[placeholder="例如 PROD0001"]').element).toMatchObject({
      value: "P009",
    });
    expect(wrapper.get('select[aria-label="站点"]').element).toMatchObject({ value: "id" });
    expect(api.listProductReviews).toHaveBeenCalledWith(
      expect.objectContaining({ product_id: "P009", site: "id" }),
    );
    expect(api.createReviewAnalysis).not.toHaveBeenCalled();
  });

  it("searches original text or Chinese translation and keeps it in analysis scope", async () => {
    const wrapper = await mountView();
    await flushPromises();
    await wrapper.get('input[placeholder="搜索原文或中文译文"]').setValue("配送延迟");
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("刷新评论"))
      ?.trigger("click");
    await flushPromises();
    expect(api.listProductReviews).toHaveBeenLastCalledWith(
      expect.objectContaining({ keyword: "配送延迟" }),
    );
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析当前范围"))
      ?.trigger("click");
    await flushPromises();
    expect(api.createReviewAnalysis).toHaveBeenCalledWith(
      expect.objectContaining({ keyword: "配送延迟" }),
    );
  });

  it("uses a fixed supported-language selector for listing and analysis", async () => {
    const wrapper = await mountView();
    await flushPromises();
    const languageSelect = wrapper.get('select[aria-label="语言"]');
    expect(languageSelect.findAll("option").map((option) => option.text())).toEqual([
      "请选择语言",
      "全部语言",
      "英语",
      "菲律宾语",
      "印度尼西亚语",
      "马来语",
      "泰语",
      "越南语",
    ]);
    await languageSelect.setValue("Vietnamese");
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("刷新评论"))
      ?.trigger("click");
    await flushPromises();
    expect(api.listProductReviews).toHaveBeenLastCalledWith(
      expect.objectContaining({ language: "Vietnamese" }),
    );
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析当前范围"))
      ?.trigger("click");
    await flushPromises();
    expect(api.createReviewAnalysis).toHaveBeenCalledWith(
      expect.objectContaining({ languages: ["Vietnamese"] }),
    );
  });

  it("uses the same sentiment wording in filters, rows, and summary", async () => {
    const wrapper = await mountView();
    await flushPromises();
    const sentimentSelect = wrapper.get('select[aria-label="情感分类"]');
    expect(sentimentSelect.findAll("option").map((option) => option.text())).toEqual([
      "请选择",
      "全部分类",
      "正向",
      "中性",
      "含改进信号",
    ]);
    expect(wrapper.text()).not.toContain("列表情感");
    expect(wrapper.text()).not.toContain("负面");
  });

  it("filters by the complete structured topic set rather than keyword text", async () => {
    api.listProductReviews.mockResolvedValue([
      {
        ...review,
        review_id: "REV-MATERIAL",
        issue_type: "other",
        topics: ["material", "packaging"],
        content: "Feels sturdy.",
      },
      { ...review, review_id: "REV-OTHER", issue_type: "other", content: "Unexpected concern." },
    ]);
    const wrapper = await mountView();
    await flushPromises();
    expect(wrapper.get("#review-REV-MATERIAL").text()).toContain("产品、包装");
    const topicSelect = wrapper.get('select[aria-label="评论主题"]');
    expect(topicSelect.findAll("option").map((option) => option.text())).toEqual([
      "请选择",
      "全部主题",
      "产品",
      "包装",
      "文案",
      "物流",
      "服务",
      "其他",
    ]);
    await topicSelect.setValue("product_quality");
    expect(wrapper.text()).toContain("Feels sturdy.");
    expect(wrapper.text()).not.toContain("Unexpected concern.");
    expect(wrapper.text()).toContain("按商品、关键词、站点、语言、评分和日期选择分析范围");
  });

  it("localizes stored language, sentiment, and issue codes for Chinese users", async () => {
    api.listProductReviews.mockResolvedValue([
      { ...review, review_id: "REV-WRONG", issue_type: "wrong_item" },
      {
        ...review,
        review_id: "REV-POSITIVE",
        rating: 5,
        sentiment_hint: "positive",
        issue_type: "no_clear_issue",
      },
      { ...review, review_id: "REV-OTHER", issue_type: "other" },
    ]);
    const wrapper = await mountView();
    await flushPromises();
    expect(wrapper.text()).toContain("产品");
    expect(wrapper.text()).toContain("正向");
    expect(wrapper.text()).toContain("其他");
    expect(wrapper.text()).toContain("其他");
    expect(wrapper.text()).not.toContain("wrong_item");
    expect(wrapper.text()).not.toContain("no_clear_issue");
    expect(wrapper.text()).not.toMatch(/\bother\b/);
    expect(wrapper.text()).not.toContain("positive");
  });

  it("runs analysis and locates representative evidence", async () => {
    const wrapper = await mountView();
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析当前范围"))
      ?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("评论概览");
    expect(wrapper.text()).toContain("评论分析结果");
    expect(wrapper.text()).toContain("改进信号");
    expect(wrapper.text()).toContain("情感分类");
    expect(wrapper.text()).toContain("评论主题");
    expect(wrapper.text()).toContain("高频痛点");
    expect(wrapper.text()).toContain("包装1 条");
    expect(wrapper.text()).not.toContain("建议关注方向");
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "REV1")
      ?.trigger("click");
    expect(wrapper.get("#review-REV1").classes()).toContain("selected");
  });

  it("uses analysis judgements after running so list and sentiment summary reconcile", async () => {
    api.listProductReviews.mockResolvedValue([
      {
        ...review,
        rating: 3,
        sentiment_hint: "neutral",
        issue_type: "none",
        content: "It works as described, though the finish is fairly basic.",
      },
    ]);
    api.runReviewAnalysis.mockResolvedValue({
      ...result,
      sentiment: { positive: 0, neutral: 0, negative: 1 },
      judgements: [
        {
          review_id: "REV1",
          product_id: "PROD0001",
          site: "sg",
          rating: 3,
          original_content: "It works as described, though the finish is fairly basic.",
          translated_content: "功能符合描述，不过做工比较基础。",
          display_content: "功能符合描述，不过做工比较基础。",
          declared_language: "English",
          detected_language: "en",
          translation_status: "available",
          sentiment: "negative",
          topics: ["product_quality"],
          confidence: "0.82",
          origin: "rule",
          source_created_at: "2026-01-01T00:00:00Z",
          quality_flags: [],
        },
      ],
    });
    const wrapper = await mountView();
    await flushPromises();
    expect(wrapper.text()).toContain("中性");
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析当前范围"))
      ?.trigger("click");
    await flushPromises();
    expect(wrapper.get("#review-REV1").text()).toContain("含改进信号");
    expect(wrapper.get("#review-REV1").text()).toContain("产品");
    expect(wrapper.get(".analysis-summary").text()).toContain("0 中性");
  });

  it("reconciles filtered and analyzed review counts with exclusion reasons", async () => {
    api.runReviewAnalysis.mockResolvedValue({
      ...result,
      quality: {
        received_count: 19,
        included_count: 16,
        excluded_count: 3,
        flag_counts: { duplicate: 2, spam: 1 },
        excluded_review_ids: ["REV17", "REV18", "REV19"],
      },
      sentiment: { positive: 8, neutral: 0, negative: 8 },
    });
    const wrapper = await mountView();
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析当前范围"))
      ?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("8 / 16 条有效评论");
    expect(wrapper.text()).toContain(
      "筛选到 19 条，纳入分析 16 条，排除 3 条（重复 2 条、垃圾内容 1 条）",
    );
    expect(wrapper.text()).toContain("评论主题");
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
      .find((button) => button.text().includes("分析当前范围"))
      ?.trigger("click");
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("包装"))
      ?.trigger("click");
    await flushPromises();
    expect(api.listReviewEvidence).toHaveBeenLastCalledWith("A1", 1, "topic", "packaging");
    expect(wrapper.text()).toContain("同一评论的多个改进方向合并展示");
  });

  it("does not display stale mismatch evidence for explicitly matching descriptions", async () => {
    api.listReviewEvidence.mockResolvedValue({
      items: [
        {
          id: "E-STALE",
          review_id: "REV1",
          language: "en",
          rating: 5,
          evidence_type: "topic",
          label: "description_mismatch",
          sentiment: "positive",
          issue_type: "description_mismatch",
          original_content: "The color matches the photos and it works as described.",
          translated_content: "颜色与图片一致，功能符合描述。",
          source_created_at: "2026-01-01T00:00:00Z",
          confidence: "0.82",
          is_mock_data: true,
        },
      ],
      page: 1,
      page_size: 20,
      total: 1,
    });
    const wrapper = await mountView();
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析当前范围"))
      ?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("暂无匹配证据");
    expect(wrapper.get(".evidence-card").text()).not.toContain("描述不符");
  });

  it("does not include positive topic mentions in improvement evidence", async () => {
    api.listReviewEvidence.mockResolvedValue({
      items: [
        {
          id: "E-POSITIVE-QUALITY",
          review_id: "REV00126",
          language: "en",
          rating: 5,
          evidence_type: "topic",
          label: "product_quality",
          sentiment: "positive",
          issue_type: "product_quality",
          original_content: "The finish is clean and the size is exactly right for me.",
          translated_content: "做工整洁，尺寸对我来说正合适。",
          source_created_at: "2026-01-01T00:00:00Z",
          confidence: "0.9",
          is_mock_data: true,
        },
        {
          id: "E-POSITIVE-SIZE",
          review_id: "REV00126",
          language: "en",
          rating: 5,
          evidence_type: "topic",
          label: "size_specification",
          sentiment: "positive",
          issue_type: "size_specification",
          original_content: "The finish is clean and the size is exactly right for me.",
          translated_content: "做工整洁，尺寸对我来说正合适。",
          source_created_at: "2026-01-01T00:00:00Z",
          confidence: "0.9",
          is_mock_data: true,
        },
      ],
      page: 1,
      page_size: 20,
      total: 2,
    });
    const wrapper = await mountView();
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("分析当前范围"))
      ?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("暂无匹配证据");
    expect(wrapper.text()).not.toContain("肯定 · 做工/质量良好");
    expect(wrapper.text()).not.toContain("肯定 · 尺寸合适");
  });
});
