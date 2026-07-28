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
    expect(wrapper.findAll(".mock-image")).toHaveLength(3);
    expect(wrapper.get(".commerce-pagination").text()).toContain("共 100 条 · 第 1 / 10 页");
    expect(wrapper.findAll("tbody tr")).toHaveLength(10);
    expect(wrapper.get(".form-grid select").findAll("option")).toHaveLength(9);
    expect(wrapper.text()).toContain("系统状态代码：active");
    expect(wrapper.get('input[value="Active"]').exists()).toBe(true);

    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("手工新建"))!
      .trigger("click");
    expect(wrapper.text()).toContain("未命名商品");
    await wrapper.get(".form-grid select").setValue("zh-CN");
    expect(wrapper.text()).toContain("待翻译");
    expect(wrapper.text()).toContain("机器翻译服务未配置");
    expect(wrapper.get(".form-grid textarea").element).toHaveProperty("value", "");
    expect(wrapper.get('input[placeholder="待补充简体中文类目"]').element).toHaveProperty(
      "value",
      "",
    );
    expect(wrapper.text()).toContain("系统状态代码：draft");
    expect(wrapper.text()).toContain("草稿");
    expect(wrapper.text()).toContain("价格（SGD）");
    await wrapper.get(".form-grid textarea").setValue("本地中文商品描述");
    expect(wrapper.get(".form-grid textarea").element).toHaveProperty("value", "本地中文商品描述");
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
    expect(wrapper.findAll(".commerce-pagination")).toHaveLength(2);
    expect(wrapper.findAll(".commerce-pagination")[1]?.text()).toContain(
      "共 260 条 · 第 1 / 26 页",
    );

    const incompleteRow = wrapper
      .findAll("tbody tr")
      .find((row) => row.text().includes("字段缺失演示草稿"));
    await incompleteRow!
      .findAll("button")
      .find((button) => button.text().includes("模拟上架"))!
      .trigger("click");
    expect(wrapper.text()).toContain("模拟上架失败");

    const adjustButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("调整 10"));
    await adjustButton!.trigger("click");
    expect(wrapper.text()).toContain("正式执行仍需创建待确认任务");
    expect(wrapper.text()).toContain("→");
  });

  it("订单页展示脱敏买家、商品、物流和售后区域", () => {
    const wrapper = mount(OrdersView);
    expect(wrapper.get(".commerce-pagination").text()).toContain("共 500 条 · 第 1 / 50 页");
    expect(wrapper.text()).toContain("（已脱敏）");
    expect(wrapper.text()).toContain("商品明细");
    expect(wrapper.text()).toContain("USB-C Hub Essential 001");
    expect(wrapper.text()).toContain("Shipment information received");
    expect(wrapper.text()).toContain("订单状态流转记录");
    expect(wrapper.text()).toContain("支付完成");
    expect(wrapper.text()).toContain("商品发货");
    expect(wrapper.text()).toContain("物流运单与轨迹");
    expect(wrapper.text()).toContain("取消、退款、退货和包裹异常");
    expect(wrapper.text()).toContain("关联客服与 AI 建议");
    expect(wrapper.text()).not.toContain("BUYER0001");
  });

  it("订单页可以关联真实 Mock 客服会话", async () => {
    const wrapper = mount(OrdersView);
    await wrapper.get('input[placeholder="搜索订单号或买家"]').setValue("ORD000252");
    await wrapper.get("tbody tr").trigger("click");

    expect(wrapper.text()).toContain("SES00001");
    expect(wrapper.text()).toContain("size_inquiry");
    expect(wrapper.text()).toContain("The mock conversation has been saved");
  });

  it("订单页根据真实物流状态展示异常", async () => {
    const wrapper = mount(OrdersView);
    await wrapper.get('input[placeholder="搜索订单号或买家"]').setValue("ORD000109");
    await wrapper.get("tbody tr").trigger("click");

    expect(wrapper.text()).toContain("物流状态exception");
    expect(wrapper.text()).toContain("异常 ·");
    expect(wrapper.text()).toContain("Temporary routing exception; manual review required");
  });
});
