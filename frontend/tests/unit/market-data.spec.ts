import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";
import * as XLSX from "xlsx";

import MarketDataView from "@/views/commerce/MarketDataView.vue";

describe("市场数据页面", () => {
  beforeEach(() => window.localStorage.clear());

  it("对项目商品执行筛选和分页", async () => {
    const wrapper = mount(MarketDataView);
    await wrapper.vm.$nextTick();

    expect(wrapper.findAll("tbody tr")).toHaveLength(10);
    expect(wrapper.text()).toContain("共 100 条 · 第 1 / 10 页");

    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("下一页"))!
      .trigger("click");
    expect(wrapper.text()).toContain("第 2 / 10 页");

    await wrapper.get('select[aria-label="站点筛选"]').setValue("Singapore");
    expect(wrapper.text()).toContain("第 1 /");
    expect(wrapper.findAll("tbody tr").length).toBeLessThanOrEqual(10);

    await wrapper.get('select[aria-label="每页条数"]').setValue("20");
    expect(wrapper.findAll("tbody tr").length).toBeLessThanOrEqual(20);
  });

  it("导入 CSV 后展示指标、来源和候选操作", async () => {
    const wrapper = mount(MarketDataView);
    const csv = [
      "title,price,rating,review_count,sales_count,updated_at,is_mock_data",
      "USB-C Hub,19.9,4.8,20,88,2026-07-01,true",
    ].join("\n");
    const file = new File([csv], "products.csv", { type: "text/csv" });

    Object.defineProperty(wrapper.get('input[type="file"]').element, "files", {
      value: [file],
    });
    await wrapper.get('input[type="file"]').trigger("change");
    await new Promise((resolve) => window.setTimeout(resolve, 0));

    expect(wrapper.text()).toContain("USB-C Hub");
    expect(wrapper.text()).toContain("simulated_experiment");
    expect(wrapper.text()).toContain("products.csv（1 条）");
    expect(wrapper.text()).toContain("商品与评论分别保留");

    await wrapper.get(".actions .sp-button--ghost").trigger("click");
    await wrapper.vm.$nextTick();
    expect(wrapper.get(".detail-drawer").text()).toContain("USB-C Hub");

    await wrapper.get(".actions .sp-button--secondary").trigger("click");
    expect(wrapper.text()).toContain("移出候选");
    wrapper.unmount();
  });

  it("同时保留商品与评论并在商品详情中展示关联评论", async () => {
    const wrapper = mount(MarketDataView);
    const products = [
      "product_id,title,price,rating,review_count,is_mock_data",
      "PROD1001,USB-C Hub,19.9,4.8,1,true",
    ].join("\n");
    const reviews = [
      "review_id,product_id,rating,content,content_zh,language,created_at,is_mock_data",
      "REV1001,PROD1001,5,Very useful,非常实用,English,2026-07-01T10:00:00+08:00,true",
    ].join("\n");
    const input = wrapper.get('input[type="file"]');

    Object.defineProperty(input.element, "files", {
      configurable: true,
      value: [
        new File([products], "products.csv", { type: "text/csv" }),
        new File([reviews], "reviews.csv", { type: "text/csv" }),
      ],
    });
    await input.trigger("change");
    await new Promise((resolve) => window.setTimeout(resolve, 0));

    expect(wrapper.text()).toContain("1关联评论");
    expect(wrapper.text()).toContain("USB-C Hub");
    expect(wrapper.findAll("tbody tr")).toHaveLength(1);

    await wrapper.get(".actions .sp-button--ghost").trigger("click");
    await wrapper.vm.$nextTick();

    expect(wrapper.get(".detail-drawer").text()).toContain("关联评论（1）");
    expect(wrapper.get(".detail-drawer").text()).toContain("Very useful");
    expect(wrapper.get(".detail-drawer").text()).toContain("中文：非常实用");
    wrapper.unmount();
  });

  it("接受 Excel 工作簿", async () => {
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet([{ category_name: "Home", search_index: 92 }]),
      "market",
    );
    const file = new File(
      [XLSX.write(workbook, { type: "array", bookType: "xlsx" })],
      "market.xlsx",
    );
    const wrapper = mount(MarketDataView);

    Object.defineProperty(wrapper.get('input[type="file"]').element, "files", {
      value: [file],
    });
    await wrapper.get('input[type="file"]').trigger("change");
    await new Promise((resolve) => window.setTimeout(resolve, 0));

    expect(wrapper.text()).toContain("Home");
    expect(wrapper.text()).toContain("market.xlsx");
  });

  it("展示、筛选并持久化选品候选", async () => {
    const wrapper = mount(MarketDataView);
    await wrapper.vm.$nextTick();

    const firstRow = wrapper.get("tbody tr");
    const productTitle = firstRow.get("td").text();
    await firstRow.get(".actions .sp-button--secondary").trigger("click");

    expect(wrapper.text()).toContain("1选品候选");
    expect(window.localStorage.getItem("sellpilot_market_candidate_product_ids")).toContain(
      "PROD0001",
    );

    await wrapper.get(".candidate-metric").trigger("click");
    expect(wrapper.get(".candidate-list").text()).toContain("选品候选列表");
    expect(wrapper.get(".candidate-list").text()).toContain("PROD0001");

    await wrapper.get(".candidate-filter input").setValue(true);
    expect(wrapper.findAll("tbody tr")).toHaveLength(1);
    expect(wrapper.get("tbody tr").text()).toContain(productTitle);

    wrapper.unmount();
    const restored = mount(MarketDataView);
    await restored.vm.$nextTick();
    expect(restored.text()).toContain("1选品候选");
  });
});
