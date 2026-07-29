const REVIEW_MODULE_LAST_ROUTE_KEY = "sellpilot_review_module_last_route";
const REVIEW_ROOT = "/market/reviews";
const IMPROVEMENT_PREFIX = "/market/reviews/improvement?analysis_id=";

export function rememberReviewModuleRoute(fullPath: string): void {
  if (fullPath.startsWith(REVIEW_ROOT)) {
    window.sessionStorage.setItem(REVIEW_MODULE_LAST_ROUTE_KEY, fullPath);
  }
}

export function resolveReviewModuleEntry(toPath: string, fromPath: string): string | null {
  if (toPath !== REVIEW_ROOT || fromPath.startsWith(REVIEW_ROOT)) return null;
  const lastRoute = window.sessionStorage.getItem(REVIEW_MODULE_LAST_ROUTE_KEY);
  return lastRoute?.startsWith(IMPROVEMENT_PREFIX) ? lastRoute : null;
}
