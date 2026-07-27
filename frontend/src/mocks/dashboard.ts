import type { DashboardMetric, FunnelStage, HealthPoint, RiskOperation } from "@/types/dashboard";

export const funnelStages: FunnelStage[] = [
  { id: "market", label: "市场商品", count: 1280, percentage: 100 },
  { id: "candidate", label: "选品候选", count: 320, percentage: 25 },
  { id: "draft", label: "上架草稿", count: 86, percentage: 6.7 },
  { id: "published", label: "模拟上架", count: 42, percentage: 3.3 },
];

export const dashboardMetrics: DashboardMetric[] = [
  { id: "margin", label: "预计毛利率", value: "34.8%", tone: "pink", icon: "trend" },
  { id: "reply", label: "客服及时回复率", value: "92%", tone: "blue", icon: "message" },
  { id: "sku", label: "活跃 SKU", value: "186", tone: "navy", icon: "package" },
];

export const healthPoints: HealthPoint[] = [
  { id: "w1", label: "第1周", value: 68 },
  { id: "w2", label: "第2周", value: 74 },
  { id: "w3", label: "第3周", value: 78 },
  { id: "w4", label: "本周", value: 82 },
];

export const riskOperations: RiskOperation[] = [
  {
    id: "risk-a12",
    name: "无线耳机",
    code: "A12",
    initials: "A12",
    risk: 4,
    factor: "近 7 日差评上升",
    impact: 18600,
    suggestion: "检查电池续航和包装说明",
    tone: "pink",
  },
  {
    id: "risk-b07",
    name: "折叠支架",
    code: "B07",
    initials: "B07",
    risk: 4,
    factor: "库存低于预警阈值",
    impact: 7200,
    suggestion: "优先补货高销量 SKU",
    tone: "blue",
  },
  {
    id: "risk-c03",
    name: "收纳包",
    code: "C03",
    initials: "C03",
    risk: 3,
    factor: "物流延迟投诉增加",
    impact: 9800,
    suggestion: "检查承运商时效",
    tone: "purple",
  },
];
