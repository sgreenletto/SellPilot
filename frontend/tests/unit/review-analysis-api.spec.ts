import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createReviewAnalysis,
  listProductReviews,
  listReviewEvidence,
} from "@/api/review-analysis";
import { request } from "@/api/http";

vi.mock("@/api/http", () => ({ request: vi.fn() }));

describe("review analysis API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.setItem("sellpilot_token", "test-token");
  });

  it("encodes bounded review filters", async () => {
    vi.mocked(request).mockResolvedValue([]);
    await listProductReviews({ product_id: "P 1", site: "sg", min_rating: 2, limit: 20 });
    expect(vi.mocked(request).mock.calls[0]?.[0]).toContain(
      "product_id=P+1&site=sg&min_rating=2&limit=20",
    );
  });

  it("uses authenticated create and evidence endpoints", async () => {
    vi.mocked(request).mockResolvedValue({} as never);
    await createReviewAnalysis({
      idempotency_key: "review-key",
      product_id: "P1",
      site: "sg",
      languages: [],
      batch_size: 100,
      maximum_reviews: 1000,
      max_attempts: 2,
    });
    await listReviewEvidence("analysis/1", 2, "topic", "packaging");
    expect(vi.mocked(request).mock.calls[0]?.[1]?.headers).toEqual({
      Authorization: "Bearer test-token",
    });
    expect(vi.mocked(request).mock.calls[1]?.[0]).toContain(
      "analyses/analysis%2F1/evidence?page=2&page_size=20&evidence_type=topic&label=packaging",
    );
  });
});
