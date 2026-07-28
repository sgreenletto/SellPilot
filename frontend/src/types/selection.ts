export type SiteCode = "sg" | "my" | "ph" | "th" | "vn" | "id";
export type CurrencyCode = "SGD" | "MYR" | "PHP" | "THB" | "VND" | "IDR";
export type SelectionRiskPreference = "conservative" | "balanced" | "growth";
export type SelectionSortField = "sales_count" | "rating" | "review_count" | "price" | "updated_at";

export interface SelectionCandidateQuery {
  site: SiteCode;
  category_id?: string;
  product_ids?: string[];
  min_price?: number;
  max_price?: number;
  sort_by?: SelectionSortField;
  descending?: boolean;
  offset?: number;
  limit?: number;
}

export interface SelectionAnalysisRequest extends SelectionCandidateQuery {
  minimum_profit: number;
  minimum_margin: number;
  platform_fee_rate: number;
  other_costs: number;
  cost_override?: number;
  shipping_cost_override?: number;
  product_weight_kg?: number;
  risk_preference: SelectionRiskPreference;
}

export interface SelectionCandidate {
  product_id: string;
  title: string;
  category_id: string;
  category_name: string;
  site: SiteCode;
  currency: CurrencyCode;
  price: string;
  cost: string;
  shipping_cost: string;
  sales_count: number;
  rating: string;
  review_count: number;
  search_index: string | null;
  sales_index: string | null;
  competition_index: string | null;
  growth_rate: string | null;
  source_name: string;
  is_mock_data: boolean;
}

export interface MetricEvidence {
  score: string | null;
  configured_weight: string;
  effective_weight: string;
  inputs: Record<string, string | number | null>;
  formula: string;
  missing_reason?: string | null;
}

export interface SelectionExplanationEvidence {
  metric: string;
  value: string;
  source: string;
}

export interface SelectionExplanation {
  summary: string;
  evidence: SelectionExplanationEvidence[];
  risks: string[];
  generation_mode: "rule_template" | "validated_generator";
}

export interface SelectionResult {
  id: string;
  product_id: string;
  title: string | null;
  rank: number;
  total_score: string;
  data_completeness: string;
  currency: CurrencyCode;
  site: SiteCode;
  profit: Record<string, string>;
  metrics: Record<string, MetricEvidence>;
  explanation: SelectionExplanation;
  risk_warnings: string[];
  evidence: Record<string, unknown>;
  is_mock_data: boolean;
}

export interface SelectionAnalysis {
  task_id: string;
  agent_task_id: string;
  status: "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED" | "ARCHIVED";
  formula_version: string;
  generation_mode: "rule_template" | "validated_generator";
  total_candidates: number;
  ranked_count: number;
  excluded_count: number;
  results: SelectionResult[];
  excluded: Record<string, unknown>[];
  is_mock_data: boolean;
}

export interface SelectionTask {
  task_id: string;
  agent_task_id: string | null;
  status: SelectionAnalysis["status"];
  criteria: Record<string, unknown>;
  formula_version: string;
  is_mock_data: boolean;
  results: SelectionResult[];
}

export interface SelectionExport {
  filename: string;
  content_type: "application/json";
  checksum_sha256: string;
  task: SelectionTask;
}
