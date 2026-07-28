import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  generateImprovementReport,
  requestImprovementDraft,
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
    await generateImprovementReport("analysis/1");
    await updateImprovementSuggestion("suggestion/1", { status: "ACCEPTED" });
    expect(vi.mocked(request).mock.calls[0]?.[0]).toBe("/v1/product-improvement/reports");
    expect(vi.mocked(request).mock.calls[0]?.[1]?.headers).toEqual({
      Authorization: "Bearer signed-test-token",
    });
    expect(vi.mocked(request).mock.calls[1]?.[0]).toContain("suggestion%2F1");
  });

  it("creates only a pending confirmation request for a draft", async () => {
    await requestImprovementDraft("report/1", ["S1"], "improvement-idempotency");
    expect(vi.mocked(request).mock.calls[0]?.[0]).toContain("report%2F1/draft-confirmations");
    expect(JSON.parse(String(vi.mocked(request).mock.calls[0]?.[1]?.body))).toMatchObject({
      idempotency_key: "improvement-idempotency",
      suggestion_ids: ["S1"],
    });
  });
});
