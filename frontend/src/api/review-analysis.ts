import { request } from "@/api/http";
import type {
  ProductReview,
  ReviewAnalysisCreated,
  ReviewAnalysisRequest,
  ReviewAnalysisResult,
  ReviewEvidencePage,
  ReviewQuery,
} from "@/types/review-analysis";

const TOKEN_KEY = "sellpilot_token";

function authInit(method = "GET", body?: unknown): RequestInit {
  const token = window.localStorage.getItem(TOKEN_KEY);
  return {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

function queryString(query: Record<string, unknown>): string {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  });
  return `?${params.toString()}`;
}

export const listProductReviews = (query: ReviewQuery) =>
  request<ProductReview[]>(
    `/v1/review-analysis/reviews${queryString(query as unknown as Record<string, unknown>)}`,
    authInit(),
  );

export const createReviewAnalysis = (payload: ReviewAnalysisRequest) =>
  request<ReviewAnalysisCreated>("/v1/review-analysis/analyses", authInit("POST", payload));

export const runReviewAnalysis = (analysisId: string) =>
  request<ReviewAnalysisResult>(
    `/v1/review-analysis/analyses/${encodeURIComponent(analysisId)}/run`,
    authInit("POST"),
    30_000,
  );

export const getReviewAnalysis = (analysisId: string) =>
  request<ReviewAnalysisResult>(
    `/v1/review-analysis/analyses/${encodeURIComponent(analysisId)}`,
    authInit(),
  );

export const listReviewEvidence = (
  analysisId: string,
  page: number,
  evidenceType = "",
  label = "",
) =>
  request<ReviewEvidencePage>(
    `/v1/review-analysis/analyses/${encodeURIComponent(analysisId)}/evidence${queryString({
      page,
      page_size: 20,
      evidence_type: evidenceType,
      label,
    })}`,
    authInit(),
  );
