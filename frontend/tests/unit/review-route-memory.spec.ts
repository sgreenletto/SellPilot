import { beforeEach, describe, expect, it } from "vitest";
import { rememberReviewModuleRoute, resolveReviewModuleEntry } from "@/router/review-route-memory";

describe("review module route memory", () => {
  beforeEach(() => window.sessionStorage.clear());

  it("returns to the last improvement report when entering from another module", () => {
    const reportRoute = "/market/reviews/improvement?analysis_id=A1";
    rememberReviewModuleRoute(reportRoute);
    expect(resolveReviewModuleEntry("/market/reviews", "/dashboard")).toBe(reportRoute);
  });

  it("allows an explicit return from the improvement report to review analysis", () => {
    rememberReviewModuleRoute("/market/reviews/improvement?analysis_id=A1");
    expect(resolveReviewModuleEntry("/market/reviews", "/market/reviews/improvement")).toBeNull();
  });

  it("does not redirect when no restorable report exists", () => {
    rememberReviewModuleRoute("/market/reviews");
    expect(resolveReviewModuleEntry("/market/reviews", "/dashboard")).toBeNull();
  });
});
