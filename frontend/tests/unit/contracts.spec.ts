import { describe, expect, it } from "vitest";

import {
  CONFIRMATION_STATUSES,
  CURRENCY_CODES,
  DATA_SOURCES,
  LANGUAGE_CODES,
  PRODUCT_STATUSES,
  SITE_CODES,
  TASK_STATUSES,
  TOOL_RISK_LEVELS,
} from "@/types/contracts";

describe("公共领域契约", () => {
  it("保持后端共享状态值稳定", () => {
    expect(PRODUCT_STATUSES).toEqual([
      "draft",
      "pending_confirmation",
      "published",
      "unpublished",
      "publish_failed",
      "archived",
    ]);
    expect(TASK_STATUSES).toEqual([
      "pending",
      "running",
      "waiting_confirmation",
      "succeeded",
      "failed",
      "cancelled",
    ]);
    expect(CONFIRMATION_STATUSES).toEqual([
      "pending",
      "confirmed",
      "executing",
      "succeeded",
      "failed",
      "cancelled",
    ]);
    expect(TOOL_RISK_LEVELS).toEqual(["read", "write", "high_risk"]);
  });

  it("保持站点、语言、币种和来源代码稳定", () => {
    expect(SITE_CODES).toEqual(["sg", "my", "ph", "th", "vn", "id", "tw", "br"]);
    expect(LANGUAGE_CODES).toEqual(["zh-CN", "en", "ms", "id", "th", "vi", "tl", "pt-BR", "zh-TW"]);
    expect(CURRENCY_CODES).toEqual([
      "CNY",
      "SGD",
      "MYR",
      "PHP",
      "THB",
      "VND",
      "IDR",
      "TWD",
      "BRL",
      "USD",
    ]);
    expect(DATA_SOURCES).toEqual(["mock", "imported", "collected", "generated", "manual"]);
  });
});
