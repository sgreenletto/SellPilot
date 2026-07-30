import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  generateImprovementReport,
  listImprovementDrafts,
  requestImprovementDraft,
  requestImprovementDraftHistoryClear,
  requestImprovementDraftRevision,
  updateImprovementSuggestion,
} from "@/api/product-improvement";
import { request } from "@/api/http";

vi.mock("@/api/http", () => ({ request: vi.fn() }));

describe("product improvement API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("sellpilot_token", "signed-test-token");
    vi.mocked(request).mockResolvedValue({} as never);
  });

  it("uses authenticated report and suggestion endpoints", async () => {
    await generateImprovementReport("analysis/1", true);
    await updateImprovementSuggestion("suggestion/1", { status: "ACCEPTED" });
    expect(vi.mocked(request).mock.calls[0]?.[0]).toBe("/v1/product-improvement/reports");
    expect(vi.mocked(request).mock.calls[0]?.[1]?.headers).toEqual({
      Authorization: "Bearer signed-test-token",
    });
    expect(JSON.parse(String(vi.mocked(request).mock.calls[0]?.[1]?.body))).toMatchObject({
      analysis_id: "analysis/1",
      force_regenerate: true,
    });
    expect(vi.mocked(request).mock.calls[1]?.[0]).toContain("suggestion%2F1");
  });

  it("creates only a pending confirmation request for a draft", async () => {
    await requestImprovementDraft("report/1", ["S1"], "improvement-idempotency", "sg");
    expect(vi.mocked(request).mock.calls[0]?.[0]).toContain("report%2F1/draft-confirmations");
    expect(JSON.parse(String(vi.mocked(request).mock.calls[0]?.[1]?.body))).toMatchObject({
      idempotency_key: "improvement-idempotency",
      suggestion_ids: ["S1"],
    });
  });

  it("queries and requests a new improvement draft version", async () => {
    await listImprovementDrafts("PROD/1");
    await requestImprovementDraftRevision(
      "VERSION/1",
      2,
      [{ title: "包装改良", description: "增加缓冲。" }],
      "revision-idempotency",
    );

    expect(vi.mocked(request).mock.calls[0]?.[0]).toContain("source_product_id=PROD%2F1");
    expect(vi.mocked(request).mock.calls[1]?.[0]).toContain("VERSION%2F1/revision-confirmations");
    expect(JSON.parse(String(vi.mocked(request).mock.calls[1]?.[1]?.body))).toMatchObject({
      expected_version: 2,
      items: [{ title: "包装改良", description: "增加缓冲。" }],
    });
  });

  it("creates a confirmation before clearing one product's draft history", async () => {
    await requestImprovementDraftHistoryClear("PROD/1", "clear-idempotency");

    expect(vi.mocked(request).mock.calls[0]?.[0]).toBe(
      "/v1/product-improvement/drafts/clear-confirmations",
    );
    expect(JSON.parse(String(vi.mocked(request).mock.calls[0]?.[1]?.body))).toEqual({
      idempotency_key: "clear-idempotency",
      source_product_id: "PROD/1",
    });
  });
});
