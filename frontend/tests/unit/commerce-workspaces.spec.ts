import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import InventoryView from "@/views/commerce/InventoryView.vue";
import OrdersView from "@/views/commerce/OrdersView.vue";
import ProductsView from "@/views/commerce/ProductsView.vue";

describe("成员二业务工作台", () => {
  it("商品页加载项目数据并支持新建与保存本地草稿", async () => {
    const wrapper = mount(ProductsView);
    expect(wrapper.text()).toContain("USB-C Hub Essential 001");
    expect(wrapper.text()).toContain("SKU、规格、价格和库存");

    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("手工新建"))!
      .trigger("click");
    expect(wrapper.text()).toContain("未命名商品");
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("保存为草稿"))!
      .trigger("click");
    expect(wrapper.text()).toContain("后端商品写入接口尚未开放");
  });

  it("库存页展示预警、补货建议并记录单项调整流水", async () => {
    const wrapper = mount(InventoryView);
    expect(wrapper.text()).toContain("上架草稿、预览与完整性检查");
    expect(wrapper.text()).toContain("补货建议");

    const adjustButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("调整 10"));
    await adjustButton!.trigger("click");
    expect(wrapper.text()).toContain("正式执行仍需创建待确认任务");
    expect(wrapper.text()).toContain("→");
  });

  it("订单页展示脱敏买家、商品、物流和售后区域", () => {
    const wrapper = mount(OrdersView);
    expect(wrapper.text()).toContain("（已脱敏）");
    expect(wrapper.text()).toContain("商品明细");
    expect(wrapper.text()).toContain("物流运单与轨迹");
    expect(wrapper.text()).toContain("取消、退款、退货和包裹异常");
    expect(wrapper.text()).toContain("关联客服与 AI 建议");
    expect(wrapper.text()).not.toContain("BUYER0001");
  });
});
