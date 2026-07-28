import { request } from "@/api/http";
import type {
  ConfirmationTask,
  InventoryItem,
  Logistics,
  Order,
  Product,
  ProductDraftPayload,
  ReturnRefund,
  SelectionCandidate,
} from "@/types/commerce";

const TOKEN_KEY = "sellpilot_token";

interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

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

export function confirmCommerceOperation(confirmationId: string): Promise<ConfirmationTask> {
  return request<ConfirmationTask>(
    `/v1/confirmations/${encodeURIComponent(confirmationId)}/confirm`,
    authInit("POST"),
  );
}

export function cancelCommerceOperation(confirmationId: string): Promise<ConfirmationTask> {
  return request<ConfirmationTask>(
    `/v1/confirmations/${encodeURIComponent(confirmationId)}/cancel`,
    authInit("POST"),
  );
}

export function listConfirmations(pageSize = 100): Promise<PageResult<ConfirmationTask>> {
  return request<PageResult<ConfirmationTask>>(
    `/v1/confirmations?page=1&page_size=${pageSize}`,
    authInit(),
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

export function requestProductDraft(product: ProductDraftPayload): Promise<ConfirmationTask> {
  return request<ConfirmationTask>(
    "/v1/commerce/products/draft-request",
    authInit("POST", { idempotency_key: crypto.randomUUID(), product }),
  );
}

export function requestProductImport(
  products: ProductDraftPayload[],
): Promise<ConfirmationTask> {
  return request<ConfirmationTask>(
    "/v1/commerce/products/import-request",
    authInit("POST", { idempotency_key: crypto.randomUUID(), products }),
  );
}

export function listSelectionCandidates(): Promise<SelectionCandidate[]> {
  return request<SelectionCandidate[]>("/v1/commerce/selection-candidates", authInit());
}

export function requestSelectionCandidate(
  productId: string,
  selected: boolean,
  title: string,
  sourceType: string,
  isMockData: boolean,
): Promise<ConfirmationTask> {
  const action = selected ? "add" : "remove";
  return request<ConfirmationTask>(
    `/v1/commerce/selection-candidates/${encodeURIComponent(productId)}/${action}-request`,
    authInit("POST", {
      idempotency_key: crypto.randomUUID(),
      title,
      source_type: sourceType,
      is_mock_data: isMockData,
    }),
  );
}
