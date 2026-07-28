import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  compareSelectionProducts,
  createSelectionAnalysis,
  downloadSelectionExport,
  listSelectionCandidates,
  selectionQueryString,
} from "@/api/selection";

describe("selection API client", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("serializes candidate filters without undefined values", () => {
    const query = selectionQueryString({
      site: "sg",
      category_id: "CAT-001",
      min_price: 10,
      max_price: 80,
      product_ids: ["P001", "P002"],
      offset: 20,
      limit: 20,
    });

    const params = new URLSearchParams(query.slice(1));
    expect(params.get("site")).toBe("sg");
    expect(params.get("category_id")).toBe("CAT-001");
    expect(params.getAll("product_id")).toEqual(["P001", "P002"]);
    expect(params.has("undefined")).toBe(false);
  });

  it("uses authenticated formal endpoints and converts compare ids", async () => {
    window.localStorage.setItem("sellpilot_access_token", "test-token");
    const fetchMock = vi.spyOn(window, "fetch").mockImplementation(async () => {
      return new Response(JSON.stringify({ code: 0, message: "ok", data: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    await listSelectionCandidates({ site: "sg", limit: 10 });
    await compareSelectionProducts("task-1", ["P001", "P002"]);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/v1/selection/candidates?site=sg"),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      }),
    );
    expect(fetchMock.mock.calls[1]?.[0]).toContain(
      "/v1/selection/analyses/task-1/compare?product_id=P001&product_id=P002",
    );
  });

  it("sends risk and cost inputs to the analysis API", async () => {
    const fetchMock = vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 0,
          message: "ok",
          data: {
            task_id: "task",
            agent_task_id: "agent",
            status: "SUCCEEDED",
            formula_version: "selection-v1.0.0-conservative",
            generation_mode: "rule_template",
            total_candidates: 0,
            ranked_count: 0,
            excluded_count: 0,
            results: [],
            excluded: [],
            is_mock_data: true,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await createSelectionAnalysis({
      site: "sg",
      minimum_profit: 5,
      minimum_margin: 0.1,
      platform_fee_rate: 0.08,
      other_costs: 1,
      cost_override: 20,
      shipping_cost_override: 4,
      product_weight_kg: 0.5,
      risk_preference: "conservative",
    });

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(JSON.parse(String(init.body))).toMatchObject({
      cost_override: 20,
      shipping_cost_override: 4,
      risk_preference: "conservative",
    });
  });

  it("downloads the structured export as a readable Markdown report", () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const createObjectURL = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:selection");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    const filename = downloadSelectionExport({
      filename: "selection-task-1.json",
      content_type: "application/json",
      checksum_sha256: "a".repeat(64),
      task: {
        task_id: "task-1",
        agent_task_id: "agent-1",
        status: "SUCCEEDED",
        criteria: {},
        formula_version: "selection-v1.0.0",
        is_mock_data: true,
        results: [],
      },
    });

    expect(filename).toBe("selection-task-1.md");
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
  });
});
