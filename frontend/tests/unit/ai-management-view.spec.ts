import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/api/ai-management";
import AIManagementView from "@/views/ai/AIManagementView.vue";

vi.mock("@/api/ai-management", () => ({
  getPromptTemplates: vi.fn(),
  getModelRuntime: vi.fn(),
  getMemberThreeEvaluation: vi.fn(),
}));

describe("AIManagementView", () => {
  beforeEach(() => {
    vi.mocked(api.getPromptTemplates).mockResolvedValue([]);
    vi.mocked(api.getModelRuntime).mockResolvedValue({
      provider: "offline_template",
      model_name: "qwen-plus",
      configured: true,
      base_url_configured: false,
      api_key_configured: false,
      timeout_seconds: 30,
      invocation_count: 2,
      success_count: 2,
      failure_count: 0,
      total_tokens: 0,
      estimated_cost: "0",
      average_duration_ms: 12,
    });
    vi.mocked(api.getMemberThreeEvaluation).mockResolvedValue({
      dataset_version: "member3-eval-v1.0.0",
      generated_at: "2026-07-28T00:00:00Z",
      total_cases: 3,
      passed_cases: 3,
      failed_cases: 0,
      pass_rate: 1,
      cases: [],
      limitations: ["离线模板评估不代表真实百炼模型质量。"],
    });
  });

  it("renders model state and reproducible evaluation metrics", async () => {
    const wrapper = mount(AIManagementView);
    await flushPromises();

    expect(wrapper.text()).toContain("Prompt、模型与评估");
    expect(wrapper.text()).toContain("offline_template");
    expect(wrapper.text()).toContain("100%");
    expect(wrapper.text()).toContain("离线模板评估不代表真实百炼模型质量");
  });
});
