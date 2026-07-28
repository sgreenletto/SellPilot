export interface QualityResult {
  passed: boolean;
  title_length: number;
  keyword_coverage: number;
  fact_issues: string[];
  compliance_issues: string[];
  completeness_issues: string[];
  attempts: number;
}
export interface LocalizedListing {
  title: string;
  bullet_points: string[];
  description: string;
  marketing_copy: string;
  faq: Array<{ question: string; answer: string }>;
  sku_content: Array<{ sku: string; description: string }>;
  keywords: string[];
  target_language: string;
  generation_mode: string;
}
export interface ContentGeneration {
  task_id: string;
  product_id: string;
  site: string;
  target_language: string;
  audience: string;
  selling_points: string[];
  keywords: string[];
  result: { content: LocalizedListing; quality: QualityResult };
  provider: string;
  model_name: string;
  invocation_id: string;
}
export interface ContentVersion {
  id: string;
  content_id: string;
  version: number;
  title: string;
  bullet_points: { items: string[] };
  description: string;
  marketing_copy: string;
  faq: { items: Array<Record<string, string>> } | null;
  sku_content: { items: Array<Record<string, string>> } | null;
  keywords: { items: string[] } | null;
  fact_check_result: Record<string, unknown>;
  compliance_result: Record<string, unknown>;
  change_type: string;
  change_summary: string;
  created_at: string;
}
export interface ContentVersions {
  content_id: string;
  items: ContentVersion[];
  total: number;
}
export interface ContentConfirmation {
  id: string;
  status: string;
  risk_warning: string | null;
  execution_result: {
    content_id?: string;
    version_id?: string;
    version?: number;
    status?: string;
  } | null;
}
