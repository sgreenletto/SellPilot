import { request } from "@/api/http";
import type {
  ConfirmationTask,
  InventoryItem,
  Logistics,
  Order,
  Product,
  ReturnRefund,
} from "@/types/commerce";

const TOKEN_KEY = "sellpilot_access_token";

function authInit(method = "GET", body?: unknown): RequestInit {
  const token = window.localStorage.getItem(TOKEN_KEY);
  return {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

export function listProducts(query = ""): Promise<Product[]> {
  return request<Product[]>(`/v1/commerce/products${query}`, authInit());
}

export function listInventory(query = ""): Promise<InventoryItem[]> {
  return request<InventoryItem[]>(`/v1/commerce/inventory${query}`, authInit());
}

export function listOrders(query = ""): Promise<Order[]> {
  return request<Order[]>(`/v1/commerce/orders${query}`, authInit());
}

export function getProduct(productId: string): Promise<Product> {
  return request<Product>(`/v1/commerce/products/${encodeURIComponent(productId)}`, authInit());
}

export function getOrder(orderId: string): Promise<Order> {
  return request<Order>(`/v1/commerce/orders/${encodeURIComponent(orderId)}`, authInit());
}

export function getOrderLogistics(orderId: string): Promise<Logistics> {
  return request<Logistics>(
    `/v1/commerce/orders/${encodeURIComponent(orderId)}/logistics`,
    authInit(),
  );
}

export function listReturns(query = ""): Promise<ReturnRefund[]> {
  return request<ReturnRefund[]>(`/v1/commerce/returns${query}`, authInit());
}

export function requestProductStatus(
  productId: string,
  publish: boolean,
): Promise<ConfirmationTask> {
  const action = publish ? "publish" : "unpublish";
  return request<ConfirmationTask>(
    `/v1/commerce/products/${encodeURIComponent(productId)}/${action}-request`,
    authInit("POST", { idempotency_key: crypto.randomUUID() }),
  );
}

export function requestInventoryUpdate(
  productId: string,
  skuId: string,
  availableStock: number,
): Promise<ConfirmationTask> {
  return request<ConfirmationTask>(
    `/v1/commerce/products/${encodeURIComponent(productId)}/inventory-request`,
    authInit("POST", {
      idempotency_key: crypto.randomUUID(),
      sku_id: skuId,
      available_stock: availableStock,
    }),
  );
}
