export const PRODUCT_TRANSLATION_LANGUAGES = [
  "en",
  "zh-CN",
  "zh-TW",
  "ms",
  "id",
  "th",
  "vi",
  "tl",
  "pt-BR",
] as const;

export type ProductTranslationLanguage = (typeof PRODUCT_TRANSLATION_LANGUAGES)[number];

export interface ProductTranslationSource {
  product_id: string;
  source_language: ProductTranslationLanguage;
  title: string;
  description: string;
  category_name?: string;
  specifications: Array<{
    name: string;
    value: string;
  }>;
}

export interface ProductTranslationRequest {
  source: ProductTranslationSource;
  target_languages: ProductTranslationLanguage[];
  fields: Array<"title" | "description" | "category_name" | "specifications">;
  idempotency_key: string;
}

export interface ProductTranslationProviderStatus {
  configured: boolean;
  provider: string | null;
  supported_languages: ProductTranslationLanguage[];
}

export interface ProductTranslationResult {
  language: ProductTranslationLanguage;
  title: string;
  description: string;
  category_name?: string;
  specifications: Array<{
    name: string;
    value: string;
  }>;
  provider: string;
  generated_at: string;
}

export interface ProductTranslationTask {
  task_id: string;
  confirmation_task_id: string;
  status: "pending_confirmation" | "running" | "succeeded" | "partially_failed" | "failed";
  results: ProductTranslationResult[];
  failed_languages: Array<{
    language: ProductTranslationLanguage;
    code: string;
    message: string;
  }>;
}
