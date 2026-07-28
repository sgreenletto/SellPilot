import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import * as XLSX from "xlsx";

import MarketDataView from "@/views/commerce/MarketDataView.vue";

describe("市场数据页面", () => {
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
      "title,source_type,price,rating,review_count,sales_count,updated_at,is_mock_data",
      "USB-C Hub,simulated_experiment,19.9,4.8,20,88,2026-07-01,true",
    ].join("\n");
    const file = new File([csv], "products.csv", { type: "text/csv" });

    Object.defineProperty(wrapper.get('input[type="file"]').element, "files", {
      value: [file],
    });
    await wrapper.get('input[type="file"]').trigger("change");
    await new Promise((resolve) => window.setTimeout(resolve, 0));

    expect(wrapper.text()).toContain("USB-C Hub");
    expect(wrapper.text()).toContain("simulated_experiment");
    expect(wrapper.text()).toContain("已在本地解析 1 条记录");

    await wrapper.get(".actions .sp-button--secondary").trigger("click");
    expect(wrapper.text()).toContain("移出候选");
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
});
