import { request } from "@/api/http";
import type { InventoryItem, Order, Product } from "@/types/commerce";
import type { DashboardMetric } from "@/types/dashboard";

// ---- 后端 Schema 类型（与 commerce.ts 一致）----

interface TaskListResponse {
  items: unknown[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

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
}): Promise<TaskListResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("page", String(params?.page ?? 1));
  searchParams.set("page_size", String(params?.page_size ?? 20));
  return request<TaskListResponse>(`/v1/tasks?${searchParams.toString()}`);
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
