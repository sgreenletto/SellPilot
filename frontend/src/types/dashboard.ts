export type MetricTone = "pink" | "blue" | "navy";
export type MetricIconName = "trend" | "message" | "package";

export interface FunnelStage {
  id: string;
  label: string;
  count: number;
  percentage: number;
}

export interface DashboardMetric {
  id: string;
  label: string;
  value: string;
  tone: MetricTone;
  icon: MetricIconName;
}

export interface HealthPoint {
  id: string;
  label: string;
  value: number;
}

export interface RiskOperation {
  id: string;
  name: string;
  code: string;
  initials: string;
  risk: number;
  factor: string;
  impact: number;
  suggestion: string;
  tone: "pink" | "blue" | "purple";
}
