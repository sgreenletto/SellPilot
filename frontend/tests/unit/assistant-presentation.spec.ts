import { describe, expect, it } from "vitest";

import { localizedErrorMessage, presentTaskResult } from "@/utils/assistantPresentation";

describe("Assistant real task result presentation", () => {
  it("renders review counts, sentiment, pain points, and bounded evidence", () => {
    const result = presentTaskResult("review_analysis", {
      analysis: {
        product_id: "PROD0001",
        no_data: false,
        quality: { included_count: 16 },
        sentiment: { positive: 8, neutral: 3, negative: 5 },
        topics: [{ topic: "product_quality" }],
        pain_points: [
          {
            pain_point: "物流延迟",
            negative_count: 3,
            severity: "0.75",
            evidence: [{ translated_content: "送达时间比承诺晚。" }],
          },
        ],
      },
    });

    expect(result.summary).toContain("16 条有效评论");
    expect(result.metrics).toContainEqual({
      label: "正向 / 中性 / 负向",
      value: "8 / 3 / 5",
    });
    expect(result.items[0]).toMatchObject({
      title: "物流延迟",
      subtitle: "送达时间比承诺晚。",
    });
  });

  it("renders selection Top N and distinguishes a true no-data result", () => {
    const ranked = presentTaskResult("selection", {
      no_data: false,
      analysis: {
        total_candidates: 3,
        ranked_count: 3,
        results: [
          {
            product_id: "PROD0102",
            title: "Baby Safety Corner Guards",
            rank: 1,
            total_score: "71.2261",
            data_completeness: "0.5714",
            site: "sg",
          },
        ],
      },
    });
    const noData = presentTaskResult("selection", {
      no_data: true,
      message: "当前数据集中没有匹配候选，请调整站点或类目。",
      candidate_search: { count: 0 },
      analysis: null,
    });

    expect(ranked.summary).toContain("共评估 3 个候选商品");
    expect(ranked.items[0]?.title).toBe("Baby Safety Corner Guards");
    expect(ranked.items[0]?.meta).toContain("综合得分：71.2261");
    expect(noData.summary).toContain("没有匹配候选");
    expect(noData.metrics[0]?.value).toBe("0");
  });

  it("renders generated content and the bounded compliance loop", () => {
    const result = presentTaskResult("content_generation", {
      generation: {
        product_id: "PROD0001",
        target_language: "en",
        result: {
          content: {
            title: "USB-C Hub for Everyday Work",
            bullet_points: ["Six useful ports", "Compact body", "Stable desk setup"],
            description: "A localized listing based on the imported product facts.",
            faq: [{ question: "Is it compact?", answer: "Yes, it is designed for desk use." }],
          },
        },
      },
      compliance: { passed: true },
      loop: { attempts: 2, max_attempts: 3, stop_reason: "quality_passed" },
    });

    expect(result.summary).toContain("事实与合规检查已通过");
    expect(result.metrics).toContainEqual({ label: "检查轮次", value: "2 / 3" });
    expect(result.items[0]?.title).toBe("USB-C Hub for Everyday Work");
  });

  it("renders grounded knowledge sources and refuses an empty result", () => {
    const grounded = presentTaskResult("knowledge_query", {
      answer: "Mock 店铺支持在符合条件时申请退货。",
      no_reliable_source: false,
      sources: [
        {
          document_id: "policy-1",
          source_doc: "knowledge_mock/return-policy.md",
          fragment: "退货申请需要在规定期限内提交。",
          score: 0.8,
          language: "zh-CN",
          updated_at: "2026-07-29T10:00:00Z",
        },
      ],
    });
    const empty = presentTaskResult("knowledge_query", {
      answer: "",
      no_reliable_source: true,
      sources: [],
    });

    expect(grounded.summary).toContain("支持在符合条件时申请退货");
    expect(grounded.items[0]?.title).toContain("return-policy.md");
    expect(empty.summary).toBe("当前知识库中没有找到可靠依据。");
  });

  it("renders customer risk, human handoff, evidence, and Mock send state", () => {
    const human = presentTaskResult("customer_service_reply", {
      draft: {
        reply: "该请求涉及退款投诉，需要转交人工客服处理。",
        risk_level: "high",
        requires_human: true,
        basis: [],
      },
      classification: { branch: "human", risk_level: "high" },
      simulated_send: null,
    });
    const sent = presentTaskResult("customer_service_reply", {
      draft: {
        reply: "根据商品资料生成的普通咨询回复。",
        risk_level: "read",
        requires_human: false,
        basis: [{ type: "product", product_id: "PROD0001" }],
      },
      classification: { branch: "product", risk_level: "read" },
      simulated_send: { status: "mock_sent", is_mock_data: true },
    });

    expect(human.metrics).toContainEqual({ label: "处理方式", value: "转交人工" });
    expect(sent.metrics).toContainEqual({ label: "发送状态", value: "已模拟发送" });
    expect(sent.items[0]?.subtitle).toBe("PROD0001");
  });

  it("localizes a real external provider outage without exposing internals", () => {
    expect(localizedErrorMessage("External service is unavailable")).toBe(
      "内容生成服务暂时不可用，请稍后重试。",
    );
  });
});
