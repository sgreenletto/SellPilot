import type { SiteCode } from "@/types/selection";

export type AnalysisStatus = "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED";

export interface ReviewQuery {
  product_id: string;
  site?: SiteCode;
  language?: string;
  min_rating?: number;
  max_rating?: number;
  created_from?: string;
  created_to?: string;
  offset?: number;
  limit?: number;
}

export interface ProductReview {
  review_id: string;
  product_id: string;
  site: SiteCode;
  rating: number;
  content: string;
  translated_content: string | null;
  language: string;
  sentiment_hint: string;
  issue_type: string;
  created_at: string;
  source_type: string;
  is_mock_data: boolean;
}

export interface ReviewAnalysisRequest {
  idempotency_key: string;
  product_id: string;
  site?: SiteCode;
  languages: string[];
  min_rating?: number;
  max_rating?: number;
  created_from?: string;
  created_to?: string;
  batch_size: number;
  maximum_reviews: number;
  max_attempts: number;
}

export interface ReviewAnalysisCreated {
  analysis_id: string;
  agent_task_id: string;
  status: AnalysisStatus;
  duplicate: boolean;
  analyzer_version: string;
  analysis_mode: "rule" | "validated_model";
  prompt_version: string | null;
  model_version: string | null;
  is_mock_data: boolean;
}

export interface TopicAggregate {
  topic: string;
  count: number;
  frequency_rate: string;
  negative_count: number;
  severity: string;
}

export interface PainPointAggregate {
  pain_point: string;
  negative_count: number;
  frequency_rate: string;
  severity: string;
  affected_sites: SiteCode[];
}

export interface KeywordAggregate {
  keyword: string;
  count: number;
  review_count: number;
}

export interface TrendPoint {
  site: SiteCode;
  month: string;
  review_count: number;
  negative_count: number;
  average_rating: string;
  topic_counts: Record<string, number>;
}

export interface ReviewAnalysisResult extends ReviewAnalysisCreated {
  product_id: string;
  site: SiteCode;
  progress: number;
  current_step: string | null;
  steps: Array<{ step_name: string; status: string; error_message: string | null }>;
  quality: Record<string, unknown> | null;
  sentiment: { positive: number; neutral: number; negative: number } | null;
  topics: TopicAggregate[];
  pain_points: PainPointAggregate[];
  keywords: KeywordAggregate[];
  trends: TrendPoint[];
  judgements: Array<Record<string, unknown>>;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface ReviewEvidence {
  id: string;
  review_id: string;
  language: string;
  rating: number;
  evidence_type: string;
  label: string;
  sentiment: string | null;
  issue_type: string | null;
  original_content: string;
  translated_content: string | null;
  source_created_at: string;
  confidence: string;
  is_mock_data: boolean;
}

export interface ReviewEvidencePage {
  items: ReviewEvidence[];
  page: number;
  page_size: number;
  total: number;
}
