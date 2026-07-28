import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import InventoryView from "@/views/commerce/InventoryView.vue";
import OrdersView from "@/views/commerce/OrdersView.vue";
import ProductsView from "@/views/commerce/ProductsView.vue";

const loadCommerceDashboardSnapshot = vi.fn();
const requestProductStatus = vi.fn();
const requestInventoryUpdate = vi.fn();
const confirmCommerceOperation = vi.fn();
const cancelCommerceOperation = vi.fn();
const requestProductDraft = vi.fn();
const requestProductImport = vi.fn();

vi.mock("@/api/dashboard", () => ({
  loadCommerceDashboardSnapshot: (...args: unknown[]) => loadCommerceDashboardSnapshot(...args),
}));
vi.mock("@/api/commerce", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/commerce")>()),
  requestProductStatus: (...args: unknown[]) => requestProductStatus(...args),
  requestInventoryUpdate: (...args: unknown[]) => requestInventoryUpdate(...args),
  confirmCommerceOperation: (...args: unknown[]) => confirmCommerceOperation(...args),
  cancelCommerceOperation: (...args: unknown[]) => cancelCommerceOperation(...args),
  requestProductDraft: (...args: unknown[]) => requestProductDraft(...args),
  requestProductImport: (...args: unknown[]) => requestProductImport(...args),
}));

describe("成员二业务工作台", () => {
  beforeEach(() => {
    localStorage.setItem("sellpilot_selected_shop_id", "SHOP001");
    loadCommerceDashboardSnapshot.mockReset();
    requestProductStatus.mockReset();
    requestInventoryUpdate.mockReset();
    confirmCommerceOperation.mockReset();
    cancelCommerceOperation.mockReset();
    requestProductDraft.mockReset();
    requestProductImport.mockReset();
    vi.stubGlobal(
      "confirm",
      vi.fn(() => true),
    );
    requestProductStatus.mockResolvedValue({
      id: "CONFIRMATION-001",
      operation_type: "commerce.unpublish_product",
      status: "pending",
    });
    requestInventoryUpdate.mockResolvedValue({
      id: "INVENTORY-CONFIRMATION-001",
      operation_type: "commerce.update_inventory",
      status: "pending",
    });
    confirmCommerceOperation.mockResolvedValue({
      id: "CONFIRMATION-001",
      operation_type: "commerce.unpublish_product",
      status: "confirmed",
    });
    cancelCommerceOperation.mockResolvedValue({
      id: "CONFIRMATION-001",
      operation_type: "commerce.unpublish_product",
      status: "cancelled",
    });
    requestProductDraft.mockResolvedValue({
      id: "DRAFT-CONFIRMATION-001",
      operation_type: "commerce.save_product_draft",
      status: "pending",
    });
    requestProductImport.mockResolvedValue({
      id: "IMPORT-CONFIRMATION-001",
      operation_type: "commerce.import_products",
      status: "pending",
    });
    loadCommerceDashboardSnapshot.mockResolvedValue({
      products: [
        {
          product_id: "PROD0001",
          title: "USB-C Hub Essential 001",
          category_name: "Consumer Electronics",
          currency: "SGD",
          price: "11.02",
          status: "active",
          sales_count: 10,
        },
        {
          product_id: "PROD0002",
          title: "Microfiber Towel Set Plus 002",
          category_name: "Home & Living",
          currency: "MYR",
          price: "56.87",
          status: "draft",
          sales_count: 3,
        },
      ],
      inventory: [
        {
          inventory_id: "INV00001",
          sku_id: "SKU00001",
          product_id: "PROD0001",
          warehouse_id: "WH001",
          available_stock: 138,
          reserved_stock: 2,
          safety_stock: 9,
          stock_status: "sufficient",
        },
      ],
      orders: [
        {
          order_id: "ORD000001",
          buyer_id: "BUYER0001",
          site: "Singapore",
          currency: "SGD",
          order_status: "delivered",
          payment_status: "paid",
          total_amount: "158.85",
          created_at: "2026-06-06T10:48:00+08:00",
        },
        {
          order_id: "ORD000252",
          buyer_id: "BUYER0252",
          site: "Singapore",
          currency: "SGD",
          order_status: "processing",
          payment_status: "paid",
          total_amount: "88.00",
          created_at: "2026-05-05T10:00:00+08:00",
        },
        {
          order_id: "ORD000109",
          buyer_id: "BUYER0109",
          site: "Singapore",
          currency: "SGD",
          order_status: "shipped",
          payment_status: "paid",
          total_amount: "66.00",
          created_at: "2026-04-04T10:00:00+08:00",
        },
      ],
    });
  });

  it("商品页加载项目数据并通过确认流程保存后端草稿", async () => {
    const wrapper = mount(ProductsView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("已连接后端");
    });
    expect(wrapper.text()).toContain("USB-C Hub Essential 001");
    expect(wrapper.text()).toContain("SKU、规格、价格和库存");
    expect(wrapper.findAll(".mock-image")).toHaveLength(3);
    expect(wrapper.get(".commerce-pagination").text()).toContain("共 2 条 · 第 1 / 1 页");
    expect(wrapper.findAll("tbody tr")).toHaveLength(2);
    expect(wrapper.get(".form-grid select").findAll("option")).toHaveLength(9);
    expect(wrapper.text()).toContain("系统状态代码：active");
    expect(wrapper.find('input[value="Active"]').exists()).toBe(true);

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
    await vi.waitFor(() => {
      expect(requestProductDraft).toHaveBeenCalled();
      expect(wrapper.text()).toContain("刷新页面后仍会保留");
    });
  });

  it("库存页展示预警、补货建议并记录单项调整流水", async () => {
    const wrapper = mount(InventoryView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("已连接后端");
    });

    expect(wrapper.text()).toContain("上架草稿、预览与完整性检查");
    expect(wrapper.text()).toContain("Mock 已上架");
    expect(wrapper.text()).toContain("草稿");
    expect(wrapper.text()).toContain("健康且已上架");
    expect(wrapper.text()).toContain("补货建议");
    expect(wrapper.findAll(".commerce-pagination")).toHaveLength(2);
    expect(wrapper.findAll(".commerce-pagination")[0]?.text()).toContain("共 2 条 · 第 1 / 1 页");
    expect(wrapper.findAll(".commerce-pagination")[1]?.text()).toContain("共 1 条 · 第 1 / 1 页");

    const activeRow = wrapper
      .findAll("tbody tr")
      .find((row) => row.text().includes("USB-C Hub Essential 001"));
    await activeRow!
      .findAll("button")
      .find((button) => button.text().includes("申请 Mock 下架"))!
      .trigger("click");
    await vi.waitFor(() => {
      expect(requestProductStatus).toHaveBeenCalledWith("PROD0001", false);
    });
    expect(wrapper.text()).toContain("再次确认后才会修改 Mock 平台数据");

    await activeRow!
      .findAll("button")
      .find((button) => button.text().includes("确认执行"))!
      .trigger("click");
    await vi.waitFor(() => {
      expect(confirmCommerceOperation).toHaveBeenCalledWith("CONFIRMATION-001");
    });
    expect(wrapper.text()).toContain("Mock 平台商品状态已修改");

    const adjustButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("申请调整 10"));
    await adjustButton!.trigger("click");
    await vi.waitFor(() => {
      expect(requestInventoryUpdate).toHaveBeenCalledWith("PROD0001", "SKU00001", 148);
    });
    expect(wrapper.text()).toContain("确认执行后才会修改 Mock 平台库存");

    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("确认 1 项调整"))!
      .trigger("click");
    await vi.waitFor(() => {
      expect(confirmCommerceOperation).toHaveBeenCalledWith("INVENTORY-CONFIRMATION-001");
    });
    expect(wrapper.text()).toContain("Mock 平台库存已更新");
    expect(wrapper.text()).toContain("→");
  });

  it("订单页展示脱敏买家、商品、物流和售后区域", async () => {
    const wrapper = mount(OrdersView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("已连接后端");
    });
    expect(wrapper.get(".commerce-pagination").text()).toContain("共 3 条 · 第 1 / 1 页");
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
    const wrapper = mount(OrdersView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("已连接后端");
    });
    await wrapper.get('input[placeholder="搜索订单号或买家"]').setValue("ORD000252");
    await wrapper.get("tbody tr").trigger("click");

    expect(wrapper.text()).toContain("SES00001");
    expect(wrapper.text()).toContain("size_inquiry");
    expect(wrapper.text()).toContain("The mock conversation has been saved");
  });

  it("订单页根据真实物流状态展示异常", async () => {
    const wrapper = mount(OrdersView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("已连接后端");
    });
    await wrapper.get('input[placeholder="搜索订单号或买家"]').setValue("ORD000109");
    await wrapper.get("tbody tr").trigger("click");

    expect(wrapper.text()).toContain("物流状态exception");
    expect(wrapper.text()).toContain("异常 ·");
    expect(wrapper.text()).toContain("Temporary routing exception; manual review required");
  });
});
