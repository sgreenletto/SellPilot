import { listInventory, listOrders, listProducts } from "@/api/commerce";
import type { InventoryItem, Order, Product } from "@/types/commerce";

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
