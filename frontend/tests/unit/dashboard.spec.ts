import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardView from "@/views/dashboard/DashboardView.vue";

const loadCommerceDashboardSnapshot = vi.fn();
const listConfirmations = vi.fn();

vi.mock("@/api/dashboard", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/dashboard")>()),
  loadCommerceDashboardSnapshot: (...args: unknown[]) => loadCommerceDashboardSnapshot(...args),
}));
vi.mock("@/api/commerce", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/commerce")>()),
  listConfirmations: (...args: unknown[]) => listConfirmations(...args),
}));

describe("经营看板 v2", () => {
  beforeEach(() => {
    loadCommerceDashboardSnapshot.mockReset();
    loadCommerceDashboardSnapshot.mockRejectedValue(new Error("backend unavailable"));
    listConfirmations.mockReset();
    listConfirmations.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      pages: 0,
    });
  });
  function mountDashboard() {
    return mount(DashboardView, {
      global: {
        plugins: [createPinia()],
        stubs: {
          RouterLink: {
            template: "<a><slot /></a>",
          },
          DashboardTrendChart: {
            props: ["dataset", "trendType"],
            template: '<div class="mock-chart">chart</div>',
          },
        },
      },
    });
  }

  it("渲染五个顶部指标卡", () => {
    const wrapper = mountDashboard();

    expect(wrapper.text()).toContain("商品总数");
    expect(wrapper.text()).toContain("低库存 SKU");
    expect(wrapper.text()).toContain("模拟订单数");
    expect(wrapper.text()).toContain("待处理客服会话");
    expect(wrapper.text()).toContain("待确认任务");
  });

  it("展示指标数值", () => {
    const wrapper = mountDashboard();

    expect(wrapper.text()).toContain("186");
    expect(wrapper.text()).toContain("1,247");
    expect(wrapper.text()).toContain("23");
    expect(wrapper.text()).toContain("15");
  });

  it("渲染趋势切换标签", () => {
    const wrapper = mountDashboard();

    expect(wrapper.text()).toContain("商品运营漏斗");
    expect(wrapper.text()).toContain("订单趋势");
    expect(wrapper.text()).toContain("商品热度");
    expect(wrapper.text()).toContain("评论情绪分布");
    expect(wrapper.text()).toContain("客服问题趋势");
  });

  it("渲染异常提醒与今日待办面板", () => {
    const wrapper = mountDashboard();
    const alertsCard = wrapper.get(".alerts-card");

    expect(alertsCard.text()).toContain("异常提醒");
    expect(alertsCard.text()).toContain("当前店铺暂无可展示提醒");
    expect(alertsCard.text()).not.toContain("折叠支架");
    expect(alertsCard.text()).not.toContain("无线耳机");
  });

  it("后端不可用时不显示硬编码提醒按钮", () => {
    const wrapper = mountDashboard();

    expect(wrapper.text()).not.toContain("前往补货");
    expect(wrapper.text()).not.toContain("查看会话");
    expect(wrapper.text()).not.toContain("立即处理");
  });

  it("渲染最近动态面板", () => {
    const wrapper = mountDashboard();

    expect(wrapper.text()).toContain("最近动态");
    expect(wrapper.text()).toContain("最近任务");
    expect(wrapper.text()).toContain("系统操作记录");
  });

  it("后端不可用时不显示硬编码动态内容", () => {
    const wrapper = mountDashboard();

    expect(wrapper.text()).not.toContain("无线耳机商品描述优化建议");
    expect(wrapper.text()).not.toContain("折叠支架库存补货计划");
  });

  it("五张指标卡均可点击跳转", () => {
    const wrapper = mountDashboard();
    const cards = wrapper.findAll(".metric-card");

    expect(cards).toHaveLength(5);
    cards.forEach((card) => {
      expect(card.attributes("type")).toBe("button");
    });
  });

  it("后端连接成功后展示真实经营指标", async () => {
    listConfirmations.mockResolvedValue({
      items: [
        {
          id: "CONFIRM1",
          operation_type: "commerce.publish_product",
          target_id: "PROD1",
          status: "pending",
          idempotency_key: "test-key",
          created_at: "2026-07-28T11:00:00+08:00",
        },
      ],
      total: 1,
      page: 1,
      page_size: 100,
      pages: 1,
    });
    loadCommerceDashboardSnapshot.mockResolvedValue({
      products: [
        {
          product_id: "PROD1",
          title: "Backend Product",
          category_name: "Consumer Electronics",
          price: "42.00",
          status: "active",
          sales_count: 42,
        },
        {
          product_id: "PROD2",
          title: "Incomplete Product",
          category_name: "",
          price: "18.00",
          status: "draft",
          sales_count: 2,
        },
      ],
      inventory: [
        {
          inventory_id: "INV1",
          sku_id: "SKU1",
          product_id: "PROD1",
          stock_status: "low_stock",
          available_stock: 2,
          safety_stock: 5,
          updated_at: "2026-07-28T09:00:00+08:00",
        },
      ],
      orders: [
        {
          order_id: "ORD1",
          payment_status: "pending",
          order_status: "pending_payment",
          created_at: "2026-07-28T10:00:00+08:00",
        },
      ],
    });
    const wrapper = mountDashboard();
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("已连接后端");
    });
    expect(wrapper.text()).toContain("当前店铺后端数据");

    expect(wrapper.findAll(".metric-card")[0]?.text()).toContain("商品总数");
    expect(wrapper.findAll(".metric-card")[0]?.text()).toContain("2");
    expect(wrapper.text()).toContain("店铺商品");
    expect(wrapper.text()).toContain("资料完整");
    expect(wrapper.text()).toContain("库存健康");
    expect(wrapper.text()).toContain("健康且已上架");
    expect(wrapper.findAll(".funnel-stat-item").map((item) => item.text())).toEqual([
      "2店铺商品",
      "1资料完整",
      "0库存健康",
      "0健康且已上架",
    ]);
    expect(wrapper.text()).toContain("Backend Product（SKU1）可用库存 2");
    expect(wrapper.text()).toContain("待支付订单");
    expect(wrapper.text()).toContain("待确认 Mock 操作");
    expect(wrapper.text()).toContain("前往补货");
    expect(wrapper.text()).toContain("Mock 操作确认");
    expect(wrapper.text()).toContain("后端数据加载");
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("评论情绪分布"))!
      .trigger("click");
    expect(wrapper.text()).toContain("后端商品评分代理数据");
    expect(wrapper.text()).not.toContain("折叠支架");
    expect(wrapper.text()).toContain("未接入");
  });
});
