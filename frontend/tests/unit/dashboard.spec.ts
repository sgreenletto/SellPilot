import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchFunnelData,
  fetchInventory,
  fetchOrders,
  fetchProducts,
  fetchTasks,
} from "@/api/dashboard";
import DashboardView from "@/views/dashboard/DashboardView.vue";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("vue-router", async () => {
  const actual = await vi.importActual<typeof import("vue-router")>("vue-router");
  return { ...actual, useRouter: () => ({ push }) };
});

vi.mock("@/api/dashboard", () => ({
  fetchFunnelData: vi.fn(),
  fetchInventory: vi.fn(),
  fetchOrders: vi.fn(),
  fetchProducts: vi.fn(),
  fetchTasks: vi.fn(),
}));

const products = [
  {
    product_id: "P-1",
    title: "Mock Active Product",
    site: "sg",
    category_name: "Electronics",
    currency: "SGD",
    price: "20.00",
    sales_count: 20,
    rating: "4.8",
    review_count: 8,
    status: "active",
    is_mock_data: true,
  },
  {
    product_id: "P-2",
    title: "Mock Draft Product",
    site: "sg",
    category_name: "Home",
    currency: "SGD",
    price: "15.00",
    sales_count: 10,
    rating: "4.2",
    review_count: 3,
    status: "draft",
    is_mock_data: true,
  },
];

const orders = [
  {
    order_id: "O-1",
    buyer_id: "B-1",
    site: "sg",
    currency: "SGD",
    order_status: "paid",
    payment_status: "paid",
    total_amount: "20.00",
    created_at: "2026-07-28T00:00:00Z",
    is_mock_data: true,
  },
  {
    order_id: "O-2",
    buyer_id: "B-2",
    site: "sg",
    currency: "SGD",
    order_status: "shipped",
    payment_status: "paid",
    total_amount: "15.00",
    created_at: "2026-07-28T00:00:00Z",
    is_mock_data: true,
  },
];

const inventory = [
  {
    inventory_id: "I-1",
    sku_id: "SKU-LOW",
    product_id: "P-1",
    warehouse_id: "W-1",
    available_stock: 2,
    reserved_stock: 1,
    safety_stock: 5,
    stock_status: "low_stock",
    is_mock_data: true,
  },
];

describe("经营看板 v2", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    push.mockReset();
    vi.mocked(fetchProducts).mockResolvedValue(products);
    vi.mocked(fetchOrders).mockResolvedValue(orders);
    vi.mocked(fetchInventory).mockResolvedValue(inventory);
    vi.mocked(fetchTasks).mockResolvedValue({
      items: [],
      total: 3,
      page: 1,
      page_size: 1,
      pages: 3,
    });
    vi.mocked(fetchFunnelData).mockResolvedValue([
      { label: "商品总数", count: 2, percentage: 100 },
      { label: "已激活", count: 1, percentage: 50 },
    ]);
  });

  function mountDashboard() {
    return mount(DashboardView, {
      global: {
        stubs: {
          DashboardTrendChart: {
            props: ["dataset", "trendType"],
            template: '<div class="mock-chart">chart</div>',
          },
        },
      },
    });
  }

  it("从 API 数据渲染五个顶部指标卡", async () => {
    const wrapper = mountDashboard();
    await flushPromises();

    expect(wrapper.findAll(".metric-card")).toHaveLength(5);
    expect(wrapper.text()).toContain("商品总数");
    expect(wrapper.text()).toContain("低库存 SKU");
    expect(wrapper.text()).toContain("模拟订单数");
    expect(wrapper.text()).toContain("激活商品");
    expect(wrapper.text()).toContain("任务总数");
  });

  it("展示 API 计算的指标数值", async () => {
    const wrapper = mountDashboard();
    await flushPromises();

    expect(wrapper.findAll(".metric-card__value").map((metric) => metric.text())).toEqual([
      "2SKU",
      "1项",
      "2单",
      "1SKU",
      "3项",
    ]);
  });

  it("保留五个趋势切换标签", () => {
    const wrapper = mountDashboard();

    expect(wrapper.text()).toContain("商品运营漏斗");
    expect(wrapper.text()).toContain("订单趋势");
    expect(wrapper.text()).toContain("商品热度");
    expect(wrapper.text()).toContain("评论情绪分布");
    expect(wrapper.text()).toContain("客服问题趋势");
  });

  it("根据库存和任务 API 渲染待办", async () => {
    const wrapper = mountDashboard();
    await flushPromises();

    expect(wrapper.text()).toContain("低库存预警");
    expect(wrapper.text()).toContain("SKU SKU-LOW");
    expect(wrapper.text()).toContain("当前共有 3 个任务待处理");
    expect(wrapper.text()).toContain("前往补货");
    expect(wrapper.text()).toContain("查看任务");
  });

  it("展示 API 派生的最近任务和系统活动", async () => {
    const wrapper = mountDashboard();
    await flushPromises();

    expect(wrapper.text()).toContain("1 个 SKU 库存偏低");
    expect(wrapper.text()).toContain("3 个任务");
    expect(wrapper.text()).toContain("2 个商品已同步");
    expect(wrapper.text()).toContain("2 个订单已同步");
  });

  it("调用统一 Dashboard API", async () => {
    mountDashboard();
    await flushPromises();

    expect(fetchProducts).toHaveBeenCalledWith({ limit: 100 });
    expect(fetchOrders).toHaveBeenCalledWith({ limit: 100 });
    expect(fetchInventory).toHaveBeenCalledWith({ limit: 200 });
    expect(fetchTasks).toHaveBeenCalledWith({ page_size: 1 });
    expect(fetchFunnelData).toHaveBeenCalledOnce();
  });

  it("API 失败时显示真实错误而不伪造成功", async () => {
    vi.mocked(fetchProducts).mockRejectedValueOnce(new Error("后端未连接"));
    const wrapper = mountDashboard();
    await flushPromises();

    expect(wrapper.text()).toContain("数据加载失败：后端未连接");
    expect(wrapper.text()).toContain("重试");
  });

  it("指标卡可跳转到对应业务页面", async () => {
    const wrapper = mountDashboard();
    await flushPromises();
    const cards = wrapper.findAll(".metric-card");

    expect(cards).toHaveLength(5);
    await cards[0]!.trigger("click");
    expect(push).toHaveBeenCalledWith("/products");
  });
});
