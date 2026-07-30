import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import customerMessagesCsv from "../../../data/demo/shopee_mock/customer_messages.csv?raw";
import customerSessionsCsv from "../../../data/demo/shopee_mock/customer_sessions.csv?raw";
import logisticsCsv from "../../../data/demo/shopee_mock/logistics.csv?raw";
import logisticsTracksCsv from "../../../data/demo/shopee_mock/logistics_tracks.csv?raw";
import ordersCsv from "../../../data/demo/shopee_mock/orders.csv?raw";
import type { Order } from "@/types/commerce";
import { csvRows, type SpreadsheetRow } from "@/utils/spreadsheet";
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
const getProductTranslationProviderStatus = vi.fn();
const createTask = vi.fn();
const runTask = vi.fn();
const requestProductTranslation = vi.fn();
const getProductTranslationTask = vi.fn();

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
vi.mock("@/api/product-translation", () => ({
  getProductTranslationProviderStatus: (...args: unknown[]) =>
    getProductTranslationProviderStatus(...args),
  requestProductTranslation: (...args: unknown[]) => requestProductTranslation(...args),
  getProductTranslationTask: (...args: unknown[]) => getProductTranslationTask(...args),
}));
vi.mock("@/api/tasks", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/tasks")>()),
  createTask: (...args: unknown[]) => createTask(...args),
  runTask: (...args: unknown[]) => runTask(...args),
}));

const dashboardOrders: Order[] = [
  {
    order_id: "ORD000001",
    buyer_id: "BUYER0001",
    site: "Singapore",
    currency: "SGD",
    order_status: "delivered",
    payment_status: "paid",
    total_amount: "158.85",
    created_at: "2026-06-06T10:48:00+08:00",
    is_mock_data: true,
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
    is_mock_data: true,
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
    is_mock_data: true,
  },
];

const fixtureOrders = csvRows(ordersCsv);
const fixtureLogistics = csvRows(logisticsCsv);
const fixtureTracks = csvRows(logisticsTracksCsv);
const fixtureSessions = csvRows(customerSessionsCsv);
const fixtureMessages = csvRows(customerMessagesCsv);

function requiredFixture<T>(value: T | undefined, description: string): T {
  if (value === undefined) {
    throw new Error(`Missing deterministic Commerce fixture: ${description}`);
  }
  return value;
}

function apiOrder(row: SpreadsheetRow): Order {
  return {
    order_id: String(row.order_id),
    buyer_id: String(row.buyer_id),
    site: String(row.site),
    currency: String(row.currency),
    order_status: String(row.order_status),
    payment_status: String(row.payment_status),
    total_amount: String(row.total_amount),
    created_at: String(row.created_at),
    is_mock_data: String(row.is_mock_data) === "true",
  };
}

const dashboardOrderIds = new Set(dashboardOrders.map((order) => order.order_id));
const linkedSession = requiredFixture(
  fixtureSessions.find(
    (session) =>
      dashboardOrderIds.has(String(session.order_id)) &&
      fixtureMessages.some((message) => message.session_id === session.session_id),
  ),
  "dashboard order with a linked customer session and messages",
);
const linkedMessage = requiredFixture(
  fixtureMessages.filter((message) => message.session_id === linkedSession.session_id).at(-1),
  "message linked to the selected customer session",
);
const exceptionShipment = requiredFixture(
  fixtureLogistics.find((shipment) => {
    const order = fixtureOrders.find((item) => item.order_id === shipment.order_id);
    return (
      shipment.logistics_status === "exception" &&
      order?.shop_id === "SHOP001" &&
      fixtureTracks.some(
        (track) =>
          track.tracking_number === shipment.tracking_number &&
          track.status === "exception" &&
          track.description === "Temporary routing exception; manual review required",
      )
    );
  }),
  "SHOP001 order with exception logistics and an exception track",
);
const exceptionOrder = requiredFixture(
  fixtureOrders.find((order) => order.order_id === exceptionShipment.order_id),
  "order linked to the exception shipment",
);
const exceptionTrack = requiredFixture(
  fixtureTracks.find(
    (track) =>
      track.tracking_number === exceptionShipment.tracking_number && track.status === "exception",
  ),
  "exception track linked by tracking number",
);

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
    getProductTranslationProviderStatus.mockReset();
    createTask.mockReset();
    runTask.mockReset();
    requestProductTranslation.mockReset();
    getProductTranslationTask.mockReset();
    getProductTranslationProviderStatus.mockResolvedValue({
      provider: "offline_template",
      configured: false,
      supported_languages: [],
    });
    createTask.mockResolvedValue({ id: "REPLENISHMENT-TASK-001" });
    runTask.mockResolvedValue({
      status: "succeeded",
      result: {
        shop_external_id: "SHOP001",
        analysis_days: 90,
        lead_time_days: 30,
        safety_factor: "1.50",
        formula_version: "replenishment-v1.0.0",
        summary: {
          analyzed_skus: 1,
          replenishment_skus: 1,
          critical_skus: 1,
          recommended_units: 24,
        },
        recommendations: [
          {
            product_id: "PROD0001",
            product_title: "USB-C Hub Essential 001",
            sku_id: "SKU00001",
            seller_sku: "CAT001-0001-01",
            available_stock: 10,
            safety_stock: 5,
            units_sold: 60,
            average_daily_sales: "2.0000",
            days_of_supply: "5.0000",
            target_stock: 34,
            recommended_quantity: 24,
            risk_level: "critical",
            reason: "30日销量60件，目标库存34件，当前可用10件。",
            is_mock_data: true,
          },
        ],
        is_mock_data: true,
      },
    });
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
      orders: dashboardOrders,
    });
  });

  it("商品页加载项目数据并通过确认流程保存后端草稿", async () => {
    const wrapper = mount(ProductsView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("USB-C Hub Essential 001");
    });
    expect(wrapper.text()).toContain("USB-C Hub Essential 001");
    expect(wrapper.text()).toContain("SKU、规格、价格和库存");
    expect(wrapper.findAll(".mock-image")).toHaveLength(3);
    expect(wrapper.get(".commerce-pagination").text()).toContain("共 2 条 · 第 1 / 1 页");
    expect(wrapper.findAll("tbody tr")).toHaveLength(2);
    expect(wrapper.get(".form-grid select").findAll("option")).toHaveLength(9);
    expect(wrapper.text()).not.toContain("系统状态代码：active");
    expect(wrapper.find('input[value="在售"]').exists()).toBe(true);
    expect(
      String((wrapper.get(".form-grid textarea").element as HTMLTextAreaElement).value).length,
    ).toBeGreaterThan(180);
    expect(wrapper.get(".form-grid textarea").element).toHaveProperty(
      "value",
      expect.stringContaining("Available ports options include 6-in-1, 8-in-1"),
    );
    expect(wrapper.get('a[href^="/products/content"]').attributes("href")).toContain(
      "product_id=PROD0001",
    );

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
    expect(wrapper.text()).not.toContain("系统状态代码：draft");
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

  it("商品页选择缺失语言后自动通过确认任务生成机器译文", async () => {
    getProductTranslationProviderStatus.mockResolvedValue({
      provider: "aliyun_bailian",
      configured: true,
      supported_languages: ["zh-CN"],
    });
    requestProductTranslation.mockResolvedValue({
      task_id: "TRANSLATION-TASK-001",
      confirmation_task_id: "TRANSLATION-CONFIRMATION-001",
      status: "pending_confirmation",
      results: [],
      failed_languages: [],
    });
    getProductTranslationTask.mockResolvedValue({
      task_id: "TRANSLATION-TASK-001",
      confirmation_task_id: "TRANSLATION-CONFIRMATION-001",
      status: "completed",
      results: [
        {
          language: "zh-CN",
          title: "USB-C 集线器",
          description: "适用于笔记本电脑和平板电脑的多接口集线器。",
          category_name: "消费电子",
          specifications: [],
        },
      ],
      failed_languages: [],
    });

    const wrapper = mount(ProductsView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => expect(wrapper.text()).toContain("USB-C Hub Essential 001"));

    await wrapper.get(".form-grid select").setValue("zh-CN");

    await vi.waitFor(() => {
      expect(requestProductTranslation).toHaveBeenCalledTimes(1);
      expect(confirmCommerceOperation).toHaveBeenCalledWith("TRANSLATION-CONFIRMATION-001");
      expect(wrapper.get('input[placeholder="待补充简体中文名称"]').element).toHaveProperty(
        "value",
        "USB-C 集线器",
      );
    });
    expect(wrapper.text()).not.toContain("百炼机器翻译");
  });

  it("库存页展示预警、补货建议并记录单项调整流水", async () => {
    const wrapper = mount(InventoryView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("USB-C Hub Essential 001");
    });

    expect(wrapper.text()).toContain("上架草稿、预览与完整性检查");
    expect(wrapper.text()).toContain("已上架");
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
      .find((button) => button.text().includes("申请模拟下架"))!
      .trigger("click");
    await vi.waitFor(() => {
      expect(requestProductStatus).toHaveBeenCalledWith("PROD0001", false);
    });
    expect(wrapper.text()).toContain("再次确认后才会修改模拟平台数据");

    await activeRow!
      .findAll("button")
      .find((button) => button.text().includes("确认执行"))!
      .trigger("click");
    await vi.waitFor(() => {
      expect(confirmCommerceOperation).toHaveBeenCalledWith("CONFIRMATION-001");
    });
    expect(wrapper.text()).toContain("模拟平台商品状态已修改");

    const adjustButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("申请调整 10"));
    await adjustButton!.trigger("click");
    await vi.waitFor(() => {
      expect(requestInventoryUpdate).toHaveBeenCalledWith("PROD0001", "SKU00001", 148);
    });
    expect(wrapper.text()).toContain("确认执行后才会修改模拟平台库存");

    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("确认 1 项调整"))!
      .trigger("click");
    await vi.waitFor(() => {
      expect(confirmCommerceOperation).toHaveBeenCalledWith("INVENTORY-CONFIRMATION-001");
    });
    expect(wrapper.text()).toContain("模拟平台库存已更新");
    expect(wrapper.text()).toContain("→");
  });

  it("库存页通过统一任务 API 展示可解释的补货决策", async () => {
    const wrapper = mount(InventoryView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => expect(wrapper.text()).toContain("USB-C Hub Essential 001"));

    const analyzeButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("生成补货建议"))!;
    expect(analyzeButton.attributes("disabled")).toBeUndefined();
    await analyzeButton.trigger("click");

    await vi.waitFor(() => {
      expect(createTask).toHaveBeenCalledWith("inventory_replenishment", {
        shop_external_id: "SHOP001",
        analysis_days: 90,
        lead_time_days: 30,
        safety_factor: "1.5",
        only_replenishment: true,
      });
      expect(runTask).toHaveBeenCalledWith("REPLENISHMENT-TASK-001");
      expect(wrapper.text()).toContain("建议合计 24 件");
      expect(wrapper.text()).toContain("30日销量60件");
    });
  });

  it("订单页展示脱敏买家、商品、物流和售后区域", async () => {
    const wrapper = mount(OrdersView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("ORD000001");
    });
    expect(wrapper.get(".commerce-pagination").text()).toContain("共 3 条 · 第 1 / 1 页");
    expect(wrapper.text()).toContain("（已脱敏）");
    expect(wrapper.text()).toContain("商品明细");
    expect(wrapper.text()).toContain("USB-C Hub Essential 001");
    expect(wrapper.text()).toContain("已收到发货信息");
    expect(wrapper.text()).toContain("订单状态流转记录");
    expect(wrapper.text()).toContain("支付完成");
    expect(wrapper.text()).toContain("商品发货");
    expect(wrapper.text()).toContain("物流运单与轨迹");
    expect(wrapper.text()).toContain("取消、退款、退货和包裹异常");
    expect(wrapper.text()).toContain("关联客服与 AI 建议");
    expect(wrapper.text()).not.toContain("BUYER0001");
    const statusBadges = wrapper.findAll("tbody .sp-badge");
    expect(statusBadges.map((badge) => badge.text())).toEqual(["已送达", "处理中", "已发货"]);
    expect(statusBadges[0]?.classes()).toContain("sp-badge--success");
    expect(statusBadges[1]?.classes()).toContain("sp-badge--primary");
    expect(statusBadges[2]?.classes()).toContain("sp-badge--info");

    loadCommerceDashboardSnapshot.mockResolvedValueOnce({
      products: [],
      inventory: [],
      orders: [{ ...dashboardOrders[0], order_status: "completed" }],
    });
    const completedWrapper = mount(OrdersView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => {
      expect(completedWrapper.get("tbody .sp-badge").text()).toBe("已完成");
    });
    expect(completedWrapper.get("tbody .sp-badge").classes()).toContain("sp-badge--purple");
  });

  it("订单页可以关联真实 Mock 客服会话", async () => {
    const wrapper = mount(OrdersView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("ORD000001");
    });
    const linkedOrderId = String(linkedSession.order_id);
    await wrapper.get('input[placeholder="搜索订单号或买家"]').setValue(linkedOrderId);
    const linkedOrderRow = wrapper
      .findAll("tbody tr")
      .find((row) => row.text().includes(linkedOrderId));
    expect(linkedOrderRow).toBeDefined();
    await linkedOrderRow!.trigger("click");

    expect(dashboardOrderIds.has(linkedOrderId)).toBe(true);
    expect(wrapper.text()).toContain(String(linkedSession.session_id));
    expect(wrapper.text()).not.toContain(String(linkedSession.intent));
    expect(wrapper.text()).toContain(String(linkedMessage.content));
    expect(wrapper.text()).toContain("已关联");
    expect(wrapper.text()).toContain("会话，建议结合买家语言生成回复草稿");
  });

  it("订单页根据真实物流状态展示异常", async () => {
    loadCommerceDashboardSnapshot.mockResolvedValueOnce({
      products: [],
      inventory: [],
      orders: [dashboardOrders[0], apiOrder(exceptionOrder)],
    });
    const wrapper = mount(OrdersView, {
      global: { plugins: [createPinia()] },
    });
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("ORD000001");
    });
    const exceptionOrderId = String(exceptionOrder.order_id);
    await wrapper.get('input[placeholder="搜索订单号或买家"]').setValue(exceptionOrderId);
    const exceptionOrderRow = wrapper
      .findAll("tbody tr")
      .find((row) => row.text().includes(exceptionOrderId));
    expect(exceptionOrderRow).toBeDefined();
    await exceptionOrderRow!.trigger("click");

    expect(exceptionShipment.order_id).toBe(exceptionOrder.order_id);
    expect(exceptionTrack.tracking_number).toBe(exceptionShipment.tracking_number);
    expect(wrapper.text()).toContain("物流状态物流异常");
    expect(wrapper.text()).toContain("异常 ·");
    expect(wrapper.text()).toContain("运输路线临时异常，需要人工处理");
  });
});
