export interface ImprovementSuggestion {
  id: string;
  suggestion_key: string;
  category: string;
  title: string;
  description: string;
  priority: number;
  severity: string;
  confidence: string;
  evidence_count: number;
  frequency_rate: string;
  evidence_review_ids: { items?: string[] };
  expected_impact: Record<string, unknown> | null;
  status: "PROPOSED" | "ACCEPTED" | "IGNORED";
}

export interface ImprovementReport {
  id: string;
  review_analysis_result_id: string;
  source_product_id: string;
  version: number;
  algorithm_version: string;
  status: string;
  source_type: string;
  is_mock_data: boolean;
  data_sources: Record<string, unknown>;
  input_conditions: Record<string, unknown>;
  summary: {
    sample_size?: number;
    suggestion_count?: number;
    limitations?: string[];
  };
  created_at: string;
  suggestions: ImprovementSuggestion[];
}

export interface ConfirmationResult {
  id: string;
  status: string;
  risk_warning: string | null;
  execution_result: Record<string, unknown> | null;
}
