export interface PromptVersionSummary {
  id: string;
  version: number;
  content: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  model_parameters: Record<string, unknown>;
  change_summary: string;
  checksum: string;
  created_at: string;
}

export interface PromptTemplateSummary {
  id: string;
  key: string;
  name: string;
  purpose: string;
  task_type: string;
  language: string;
  status: string;
  latest_version: PromptVersionSummary | null;
  version_count: number;
  created_at: string;
  updated_at: string;
}

export interface ModelRuntimeSummary {
  provider: string;
  model_name: string;
  configured: boolean;
  base_url_configured: boolean;
  api_key_configured: boolean;
  timeout_seconds: number;
  invocation_count: number;
  success_count: number;
  failure_count: number;
  total_tokens: number;
  estimated_cost: string;
  average_duration_ms: number;
}

export interface EvaluationCaseSummary {
  case_id: string;
  category: string;
  passed: boolean;
  metrics: Record<string, unknown>;
  failures: string[];
}

export interface MemberThreeEvaluationSummary {
  dataset_version: string;
  generated_at: string | null;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number;
  cases: EvaluationCaseSummary[];
  limitations: string[];
}
