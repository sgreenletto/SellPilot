import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadCommerceDashboardSnapshot } from "@/api/dashboard";
import { listInventory, listOrders, listProducts } from "@/api/commerce";
import type { Product } from "@/types/commerce";

vi.mock("@/api/commerce", () => ({
  listProducts: vi.fn(),
  listInventory: vi.fn(),
  listOrders: vi.fn(),
}));

describe("经营看板数据接口", () => {
  beforeEach(() => vi.clearAllMocks());

  it("分页读取完整商品、库存和订单数据", async () => {
    const product = (index: number): Product => ({
      product_id: `PROD${index}`,
      title: `Product ${index}`,
      site: "Singapore",
      category_name: "Demo",
      currency: "SGD",
      price: "10.00",
      sales_count: index,
      rating: "4.5",
      review_count: 1,
      status: "active",
      is_mock_data: true,
    });
    vi.mocked(listProducts)
      .mockResolvedValueOnce(Array.from({ length: 100 }, (_, index) => product(index)))
      .mockResolvedValueOnce([product(100)]);
    vi.mocked(listInventory).mockResolvedValueOnce([]);
    vi.mocked(listOrders).mockResolvedValueOnce([]);

    const snapshot = await loadCommerceDashboardSnapshot();

    expect(snapshot.products).toHaveLength(101);
    expect(listProducts).toHaveBeenNthCalledWith(1, "?offset=0&limit=100");
    expect(listProducts).toHaveBeenNthCalledWith(2, "?offset=100&limit=100");
  });

  it("将来源店铺范围传给全部经营数据接口", async () => {
    vi.mocked(listProducts).mockResolvedValueOnce([]);
    vi.mocked(listInventory).mockResolvedValueOnce([]);
    vi.mocked(listOrders).mockResolvedValueOnce([]);

    await loadCommerceDashboardSnapshot("SHOP003");

    expect(listProducts).toHaveBeenCalledWith("?offset=0&limit=100&shop_id=SHOP003");
    expect(listInventory).toHaveBeenCalledWith("?offset=0&limit=100&shop_id=SHOP003");
    expect(listOrders).toHaveBeenCalledWith("?offset=0&limit=100&shop_id=SHOP003");
  });
});
