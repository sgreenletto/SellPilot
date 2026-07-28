import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ContentWorkshopView from "@/views/content/ContentWorkshopView.vue";
import * as contentApi from "@/api/content-generation";

vi.mock("@/api/content-generation", () => ({
  cancelContentDraft: vi.fn(),
  confirmContentDraft: vi.fn(),
  generateContent: vi.fn(),
  listContentVersions: vi.fn(),
  requestContentDraft: vi.fn(),
  requestVersionRestore: vi.fn(),
}));

const generation = {
  task_id: "00000000-0000-0000-0000-000000000001",
  product_id: "PROD0001",
  site: "sg",
  target_language: "zh-CN",
  audience: "家庭用户",
  selling_points: ["便携"],
  keywords: ["家具"],
  provider: "offline_template",
  model_name: "sellpilot-localized-template-v1",
  invocation_id: "00000000-0000-0000-0000-000000000002",
  result: {
    content: {
      title: "USB-C Hub｜商品详情",
      bullet_points: ["商品：USB-C Hub", "类目：消费电子", "适合：家庭用户"],
      description: "商品原始描述：Multi-port hub",
      marketing_copy: "了解 USB-C Hub，商品信息基于已核验事实。",
      faq: [{ question: "有哪些规格？", answer: "请查看已核验商品事实。" }],
      sku_content: [{ sku: "HUB-BLACK", description: "黑色款" }],
      keywords: ["家具"],
      target_language: "zh-CN",
      generation_mode: "offline_template",
    },
    quality: {
      passed: true,
      title_length: 18,
      keyword_coverage: 1,
      fact_issues: [],
      compliance_issues: [],
      completeness_issues: [],
      attempts: 1,
    },
  },
};

describe("ContentWorkshopView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(contentApi.generateContent).mockResolvedValue(structuredClone(generation));
  });

  it("keeps the form focused without a duplicate hero", () => {
    const wrapper = mount(ContentWorkshopView);

    expect(wrapper.text()).not.toContain("商品内容工坊");
    expect(wrapper.text()).not.toContain("内容流程");
    expect(wrapper.text()).not.toContain("关键词覆盖率");
  });

  it("renders localized editable fields and supports section regeneration", async () => {
    const wrapper = mount(ContentWorkshopView);
    await wrapper.get("button").trigger("click");
    await flushPromises();

    expect(wrapper.findAll("textarea")[1]?.element.value).toContain("商品：USB-C Hub");
    expect((wrapper.get('input[aria-label="FAQ 问题"]').element as HTMLInputElement).value).toBe(
      "有哪些规格？",
    );
    expect(
      (wrapper.get('textarea[aria-label="SKU 文案"]').element as HTMLTextAreaElement).value,
    ).toBe("黑色款");

    const buttons = wrapper
      .findAll("button")
      .filter((button) => button.text().includes("重新生成"));
    await buttons[0]?.trigger("click");
    await flushPromises();
    expect(contentApi.generateContent).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain("商品标题已重新生成");

    const regenerateAll = wrapper
      .findAll("button")
      .find((button) => button.text().includes("重新生成全部内容"));
    await regenerateAll?.trigger("click");
    await flushPromises();
    expect(contentApi.generateContent).toHaveBeenCalledTimes(3);
    expect(wrapper.text()).toContain("全部内容已重新生成");
  });
});
