import { request } from "@/api/http";
import type {
  MemberThreeEvaluationSummary,
  ModelRuntimeSummary,
  PromptTemplateSummary,
} from "@/types/ai-management";

const auth = (): RequestInit => {
  const token = localStorage.getItem("sellpilot_token");
  return { headers: token ? { Authorization: `Bearer ${token}` } : {} };
};

export const getPromptTemplates = () =>
  request<PromptTemplateSummary[]>("/v1/ai-management/prompts", auth());
export const getModelRuntime = () =>
  request<ModelRuntimeSummary>("/v1/ai-management/model-runtime", auth());
export const getMemberThreeEvaluation = () =>
  request<MemberThreeEvaluationSummary>("/v1/ai-management/evaluation/member3", auth());
