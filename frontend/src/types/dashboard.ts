export type MetricTone = "pink" | "blue" | "navy" | "purple" | "green";
export type MetricIconName = "trend" | "message" | "package" | "alert" | "check";

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

// ---- 新增：经营看板 v2 ----

export interface MetricCardData {
  id: string;
  label: string;
  value: number;
  suffix?: string;
  trend?: number; // 正数为上升百分比，负数为下降
  icon: MetricIconName;
  tone: MetricTone;
  linkTo?: string;
}

export type TrendType = "funnel" | "orders" | "popularity" | "sentiment" | "service";

export interface TrendSeries {
  name: string;
  data: number[];
  color?: string;
}

export interface TrendDataset {
  categories: string[];
  series: TrendSeries[];
}

export interface AlertItem {
  id: string;
  type: "warning" | "danger" | "info";
  title: string;
  description: string;
  linkTo: string;
  linkLabel: string;
  timestamp: string;
}

export interface RecentActivity {
  id: string;
  type: "task" | "system";
  action: string;
  target: string;
  status: "completed" | "pending" | "failed" | "processing";
  timestamp: string;
}
