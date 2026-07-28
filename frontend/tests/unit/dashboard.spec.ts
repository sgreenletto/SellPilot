import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardView from "@/views/dashboard/DashboardView.vue";

const loadCommerceDashboardSnapshot = vi.fn();

vi.mock("@/api/dashboard", () => ({
  loadCommerceDashboardSnapshot: (...args: unknown[]) => loadCommerceDashboardSnapshot(...args),
}));

describe("经营看板 v2", () => {
  beforeEach(() => {
    loadCommerceDashboardSnapshot.mockReset();
    loadCommerceDashboardSnapshot.mockRejectedValue(new Error("backend unavailable"));
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

    expect(wrapper.text()).toContain("异常提醒");
    expect(wrapper.text()).toContain("低库存预警");
    expect(wrapper.text()).toContain("高风险客服消息");
    expect(wrapper.text()).toContain("待审批确认任务");
    expect(wrapper.text()).toContain("折叠支架");
    expect(wrapper.text()).toContain("无线耳机");
  });

  it("提醒项包含快捷跳转按钮", () => {
    const wrapper = mountDashboard();

    expect(wrapper.text()).toContain("前往补货");
    expect(wrapper.text()).toContain("查看会话");
    expect(wrapper.text()).toContain("立即处理");
  });

  it("渲染最近动态面板", () => {
    const wrapper = mountDashboard();

    expect(wrapper.text()).toContain("最近动态");
    expect(wrapper.text()).toContain("最近任务");
    expect(wrapper.text()).toContain("系统操作记录");
  });

  it("展示任务和系统操作记录内容", () => {
    const wrapper = mountDashboard();

    expect(wrapper.text()).toContain("AI 生成");
    expect(wrapper.text()).toContain("数据同步");
    expect(wrapper.text()).toContain("模拟上架");
    expect(wrapper.text()).toContain("状态检测");
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
    loadCommerceDashboardSnapshot.mockResolvedValue({
      products: [
        {
          product_id: "PROD1",
          title: "Backend Product",
          status: "active",
          sales_count: 42,
        },
      ],
      inventory: [
        {
          inventory_id: "INV1",
          product_id: "PROD1",
          stock_status: "low_stock",
          available_stock: 2,
          safety_stock: 5,
        },
      ],
      orders: [
        {
          order_id: "ORD1",
          created_at: "2026-07-28T10:00:00+08:00",
        },
      ],
    });
    const wrapper = mountDashboard();
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("已连接后端");
    });

    expect(wrapper.findAll(".metric-card")[0]?.text()).toContain("商品总数");
    expect(wrapper.findAll(".metric-card")[0]?.text()).toContain("1");
    expect(wrapper.text()).toContain("未接入");
  });
});
