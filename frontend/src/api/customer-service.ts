import { request } from "@/api/http"
import type { InventoryItem, Logistics, Order, Product } from "@/types/commerce"

/** 获取商品详情（用于会话右侧上下文面板） */
export function fetchProduct(productId: string): Promise<Product> {
  return request<Product>(`/v1/commerce/products/${productId}`)
}

/** 获取订单详情 */
export function fetchOrder(orderId: string): Promise<Order> {
  return request<Order>(`/v1/commerce/orders/${orderId}`)
}

/** 获取订单物流轨迹 */
export function fetchLogistics(orderId: string): Promise<Logistics> {
  return request<Logistics>(`/v1/commerce/orders/${orderId}/logistics`)
}

/** 获取库存列表 */
export function fetchInventoryBySku(params?: {
  status?: string
  limit?: number
}): Promise<InventoryItem[]> {
  const sp = new URLSearchParams()
  if (params?.status) sp.set("status", params.status)
  sp.set("limit", String(params?.limit ?? 50))
  sp.set("offset", "0")
  return request<InventoryItem[]>(`/v1/commerce/inventory?${sp.toString()}`)
}
