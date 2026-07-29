import { request } from "@/api/http";
import { listInventory, listOrders, listProducts } from "@/api/commerce";
import type { InventoryItem, Order, Product } from "@/types/commerce";
import type { PaginatedResponse, TaskDetail } from "@/types/contracts";
import type { DashboardMetric, TrendDataset } from "@/types/dashboard";

export interface CustomerServiceStats {
  pending_count: number;
}

export function fetchCustomerServiceStats(): Promise<CustomerServiceStats> {
  return request("/v1/commerce/customer-service/stats");
}

// ---- 后端 Schema 类型（与 commerce.ts 一致）----

// ---- Dashboard API ----

export function fetchProducts(params?: { status?: string; limit?: number }): Promise<Product[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  searchParams.set("limit", String(params?.limit ?? 100));
  searchParams.set("offset", "0");
  return request<Product[]>(`/v1/commerce/products?${searchParams.toString()}`);
}

export function fetchOrders(params?: { status?: string; limit?: number }): Promise<Order[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  searchParams.set("limit", String(params?.limit ?? 100));
  searchParams.set("offset", "0");
  return request<Order[]>(`/v1/commerce/orders?${searchParams.toString()}`);
}

export function fetchInventory(params?: {
  status?: string;
  limit?: number;
}): Promise<InventoryItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  searchParams.set("limit", String(Math.min(params?.limit ?? 100, 100)));
  searchParams.set("offset", "0");
  return request<InventoryItem[]>(`/v1/commerce/inventory?${searchParams.toString()}`);
}

export function fetchTasks(params?: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<TaskDetail>> {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(params?.page ?? 1));
  searchParams.set("page_size", String(params?.page_size ?? 20));
  return request<PaginatedResponse<TaskDetail>>(`/v1/tasks?${searchParams.toString()}`);
}

// ---- Funnel 数据 ----

export interface FunnelData {
  label: string;
  count: number;
  percentage: number;
}

export async function fetchFunnelData(): Promise<FunnelData[]> {
  const total = (await fetchProducts({ limit: 100 })).length;
  const active = (await fetchProducts({ status: "active", limit: 100 })).length;
  const inactive = (await fetchProducts({ status: "inactive", limit: 100 })).length;
  const draft = (await fetchProducts({ status: "draft", limit: 100 })).length;

  return [
    { label: "商品总数", count: total, percentage: 100 },
    { label: "已激活", count: active, percentage: total ? Math.round((active / total) * 100) : 0 },
    {
      label: "未激活",
      count: inactive,
      percentage: total ? Math.round((inactive / total) * 100) : 0,
    },
    { label: "草稿", count: draft, percentage: total ? Math.round((draft / total) * 100) : 0 },
  ];
}

// ---- Dashboard 指标 ----

export async function fetchDashboardMetrics(): Promise<DashboardMetric[]> {
  const [products, orders, inventory, tasks] = await Promise.all([
    fetchProducts({ limit: 100 }),
    fetchOrders({ limit: 100 }),
    fetchInventory({ limit: 200 }),
    fetchTasks({ page_size: 1 }),
  ]);

  const lowStock = inventory.filter((i) => i.stock_status === "low_stock").length;

  return [
    {
      id: "total-products",
      label: "商品总数",
      value: String(products.length),
      tone: "navy",
      icon: "package",
    },
    {
      id: "low-stock",
      label: "低库存 SKU",
      value: String(lowStock),
      tone: "pink",
      icon: "alert",
    },
    {
      id: "total-orders",
      label: "模拟订单数",
      value: String(orders.length),
      tone: "blue",
      icon: "trend",
    },
    {
      id: "margin",
      label: "预计毛利率",
      value: "34.8%",
      tone: "pink",
      icon: "trend",
    },
    {
      id: "pending-tasks",
      label: "任务总数",
      value: String(tasks.total),
      tone: "green",
      icon: "check",
    },
  ];
}

const PAGE_SIZE = 100;

async function loadAllPages<T>(
  loader: (query: string) => Promise<T[]>,
  maximumRecords: number,
): Promise<T[]> {
  const records: T[] = [];
  for (let offset = 0; offset < maximumRecords; offset += PAGE_SIZE) {
    const page = await loader(`?offset=${offset}&limit=${PAGE_SIZE}`);
    records.push(...page);
    if (page.length < PAGE_SIZE) break;
  }
  return records;
}

export interface CommerceDashboardSnapshot {
  products: Product[];
  inventory: InventoryItem[];
  orders: Order[];
}

export async function loadCommerceDashboardSnapshot(
  shopId = "all",
): Promise<CommerceDashboardSnapshot> {
  const scope = shopId === "all" ? "" : `&shop_id=${encodeURIComponent(shopId)}`;
  const [products, inventory, orders] = await Promise.all([
    loadAllPages((query) => listProducts(`${query}${scope}`), 1_000),
    loadAllPages((query) => listInventory(`${query}${scope}`), 5_000),
    loadAllPages((query) => listOrders(`${query}${scope}`), 10_000),
  ]);
  return { products, inventory, orders };
}

// ---- 评论情绪分布（基于产品评分）----

export function buildReviewSentimentTrend(snapshot: CommerceDashboardSnapshot): TrendDataset {
  const rated = snapshot.products.filter((p) => Number(p.rating) > 0);
  const bins = {
    "1-2分": 0,
    "3分": 0,
    "4分": 0,
    "5分": 0,
  };
  for (const p of rated) {
    const r = Number(p.rating);
    if (r <= 2) bins["1-2分"]++;
    else if (r < 4) bins["3分"]++;
    else if (r < 5) bins["4分"]++;
    else bins["5分"]++;
  }
  return {
    categories: Object.keys(bins),
    series: [{ name: "商品数", data: Object.values(bins), color: "green" }],
  };
}

// ---- 客服问题趋势（基于订单状态分布）----

export function buildServiceIssueTrend(snapshot: CommerceDashboardSnapshot): TrendDataset {
  const counts: Record<string, number> = {};
  for (const o of snapshot.orders) {
    const s = o.order_status || "unknown";
    counts[s] = (counts[s] ?? 0) + 1;
  }
  const entries = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  return {
    categories: entries.map(([k]) => k),
    series: [{ name: "订单数", data: entries.map(([, v]) => v), color: "blue" }],
  };
}
