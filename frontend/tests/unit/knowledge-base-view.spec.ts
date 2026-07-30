import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import KnowledgeBaseView from "@/views/knowledge-base/KnowledgeBaseView.vue";

const fetchDocuments = vi.fn();
const deleteDocument = vi.fn();
const retrieveKnowledge = vi.fn();

vi.mock("@/api/knowledge-base", () => ({
  fetchDocuments: (...args: unknown[]) => fetchDocuments(...args),
  deleteDocument: (...args: unknown[]) => deleteDocument(...args),
  retrieveKnowledge: (...args: unknown[]) => retrieveKnowledge(...args),
}));

const totals: Record<string, number> = {
  "": 1204,
  product: 103,
  faq: 100,
  review: 1000,
};

describe("KnowledgeBaseView", () => {
  beforeEach(() => {
    fetchDocuments.mockReset();
    deleteDocument.mockReset();
    retrieveKnowledge.mockReset();
    fetchDocuments.mockImplementation(
      async (params: { page_size?: number; category?: string } = {}) => ({
        items:
          params.page_size === 100
            ? [
                {
                  id: "doc-1",
                  title: "FAQ #SES00001",
                  file_type: "csv",
                  file_size_bytes: 256,
                  category: "faq",
                  status: "indexed",
                  chunk_count: 1,
                  source: "customer_messages.csv#SES00001",
                  error_message: null,
                  updated_at: "2026-07-30T00:00:00Z",
                },
              ]
            : [],
        total: totals[params.category ?? ""],
        page: 1,
        page_size: params.page_size ?? 100,
        pages: 1,
      }),
    );
  });

  it("loads category totals independently from the paged document list", async () => {
    const wrapper = mount(KnowledgeBaseView);
    await flushPromises();

    expect(wrapper.text()).toContain("全部 1204");
    expect(wrapper.text()).toContain("商品知识 103");
    expect(wrapper.text()).toContain("客服常见问题 100");
    expect(wrapper.text()).toContain("用户评论 1000");
    expect(fetchDocuments).toHaveBeenCalledWith({ page_size: 1, category: "product" });
    expect(fetchDocuments).toHaveBeenCalledWith({ page_size: 1, category: "review" });
  });
});
