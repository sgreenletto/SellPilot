import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  generateContent,
  requestContentDraft,
  requestVersionRestore,
} from "@/api/content-generation";
import { request } from "@/api/http";

vi.mock("@/api/http", () => ({ request: vi.fn() }));

describe("content generation API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("sellpilot_token", "signed-test-token");
    vi.mocked(request).mockResolvedValue({} as never);
  });

  it("uses the shared authenticated API client", async () => {
    await generateContent({ product_id: "PROD0001", site: "sg", target_language: "en" });

    expect(vi.mocked(request).mock.calls[0]?.[0]).toBe("/v1/content-generation/generate");
    expect(vi.mocked(request).mock.calls[0]?.[1]?.headers).toEqual({
      Authorization: "Bearer signed-test-token",
    });
  });

  it("requests confirmation before draft or restore writes", async () => {
    const generation = { task_id: "task-1" } as never;
    await requestContentDraft(generation, "draft-key");
    await requestVersionRestore("content/1", "version/1", "restore-key");

    expect(vi.mocked(request).mock.calls[0]?.[0]).toBe(
      "/v1/content-generation/draft-confirmations",
    );
    expect(JSON.parse(String(vi.mocked(request).mock.calls[0]?.[1]?.body))).toMatchObject({
      idempotency_key: "draft-key",
    });
    expect(vi.mocked(request).mock.calls[1]?.[0]).toContain("content%2F1/restore-confirmations");
  });
});
