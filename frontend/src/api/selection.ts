import { request } from "@/api/http";
import type {
  SelectionAnalysis,
  SelectionAnalysisRequest,
  SelectionCandidate,
  SelectionCandidateQuery,
  SelectionExport,
  SelectionResult,
  SelectionTask,
} from "@/types/selection";

const TOKEN_KEY = "sellpilot_access_token";

function authInit(method = "GET", body?: unknown): RequestInit {
  const token = window.localStorage.getItem(TOKEN_KEY);
  return {
    method,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

export function selectionQueryString(query: SelectionCandidateQuery): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === "" || value === null) continue;
    if (Array.isArray(value)) {
      value.forEach((item) => params.append(key === "product_ids" ? "product_id" : key, item));
    } else {
      params.set(key, String(value));
    }
  }
  const serialized = params.toString();
  return serialized ? `?${serialized}` : "";
}

export function listSelectionCandidates(
  query: SelectionCandidateQuery,
): Promise<SelectionCandidate[]> {
  return request<SelectionCandidate[]>(
    `/v1/selection/candidates${selectionQueryString(query)}`,
    authInit(),
  );
}

export function createSelectionAnalysis(
  payload: SelectionAnalysisRequest,
): Promise<SelectionAnalysis> {
  return request<SelectionAnalysis>("/v1/selection/analyses", authInit("POST", payload), 30_000);
}

export function getSelectionAnalysis(taskId: string): Promise<SelectionTask> {
  return request<SelectionTask>(`/v1/selection/analyses/${encodeURIComponent(taskId)}`, authInit());
}

export function compareSelectionProducts(
  taskId: string,
  productIds: string[],
): Promise<SelectionResult[]> {
  const params = new URLSearchParams();
  productIds.forEach((productId) => params.append("product_id", productId));
  return request<SelectionResult[]>(
    `/v1/selection/analyses/${encodeURIComponent(taskId)}/compare?${params.toString()}`,
    authInit(),
  );
}

export function exportSelectionAnalysis(taskId: string): Promise<SelectionExport> {
  return request<SelectionExport>(
    `/v1/selection/analyses/${encodeURIComponent(taskId)}/export`,
    authInit(),
  );
}

const metricNames: Record<string, string> = {
  demand: "需求热度",
  competition: "竞争程度",
  profitability: "利润空间",
  review_quality: "评论质量",
  logistics: "物流风险",
  after_sales: "售后风险",
  factory_fit: "工厂适配",
};

function reportRiskText(risk: string): string {
  const missingMatch = /^missing ([a-z_]+):/.exec(risk);
  if (missingMatch) {
    return `${metricNames[missingMatch[1] ?? ""] ?? missingMatch[1]}数据缺失，当前评分未计入这一项`;
  }
  if (risk === "negative profit") return "预计利润为负";
  if (risk === "negative margin") return "预计利润率为负";
  return risk;
}

function markdownReport(report: SelectionExport): string {
  const lines = [
    "# SellPilot 智能选品报告",
    "",
    `- 任务编号：${report.task.task_id}`,
    `- 评分公式：${report.task.formula_version}`,
    `- 数据类型：${report.task.is_mock_data ? "模拟实验数据" : "导入数据"}`,
    `- 入选商品：${report.task.results.length} 项`,
    "",
  ];
  report.task.results.forEach((result) => {
    lines.push(
      `## ${result.rank}. ${result.title || result.product_id}`,
      "",
      `- 商品编号：${result.product_id}`,
      `- 综合得分：${result.total_score} / 100`,
      `- 数据完整度：${(Number(result.data_completeness) * 100).toFixed(1)}%`,
      `- 预计利润：${result.currency} ${result.profit.profit ?? "—"}`,
      `- 预计利润率：${(Number(result.profit.margin ?? 0) * 100).toFixed(1)}%`,
      "",
      "### 分项评分",
      "",
      "| 指标 | 得分 |",
      "| --- | ---: |",
    );
    Object.entries(result.metrics).forEach(([key, metric]) => {
      lines.push(`| ${metricNames[key] ?? key} | ${metric.score ?? "数据缺失"} |`);
    });
    lines.push("", "### 风险提示", "");
    if (result.risk_warnings.length) {
      result.risk_warnings.forEach((risk) => lines.push(`- ${reportRiskText(risk)}`));
    } else {
      lines.push("- 暂无额外风险提示");
    }
    lines.push("");
  });
  return `${lines.join("\n")}\n`;
}

export function downloadSelectionExport(report: SelectionExport): string {
  const filename = report.filename.replace(/\.json$/i, ".md");
  const blob = new Blob([markdownReport(report)], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
  return filename;
}
