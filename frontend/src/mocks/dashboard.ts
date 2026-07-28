import type {
  AlertItem,
  DashboardMetric,
  FunnelStage,
  HealthPoint,
  MetricCardData,
  RecentActivity,
  RiskOperation,
  TrendDataset,
} from "@/types/dashboard"

// ---- 原有 mock 数据（保留兼容） ----

export const funnelStages: FunnelStage[] = [
  { id: "market", label: "市场商品", count: 1280, percentage: 100 },
  { id: "candidate", label: "选品候选", count: 320, percentage: 25 },
  { id: "draft", label: "上架草稿", count: 86, percentage: 6.7 },
  { id: "published", label: "模拟上架", count: 42, percentage: 3.3 },
]

export const dashboardMetrics: DashboardMetric[] = [
  { id: "margin", label: "预计毛利率", value: "34.8%", tone: "pink", icon: "trend" },
  { id: "reply", label: "客服及时回复率", value: "92%", tone: "blue", icon: "message" },
  { id: "sku", label: "活跃 SKU", value: "186", tone: "navy", icon: "package" },
]

export const healthPoints: HealthPoint[] = [
  { id: "w1", label: "第1周", value: 68 },
  { id: "w2", label: "第2周", value: 74 },
  { id: "w3", label: "第3周", value: 78 },
  { id: "w4", label: "本周", value: 82 },
]

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
]

// ---- 新增：经营看板 v2 数据 ----

// ---------- 顶部指标卡 ----------

export const topMetrics: MetricCardData[] = [
  {
    id: "total-products",
    label: "商品总数",
    value: 186,
    suffix: "SKU",
    trend: 12.5,
    icon: "package",
    tone: "navy",
    linkTo: "/products",
  },
  {
    id: "low-stock",
    label: "低库存 SKU",
    value: 8,
    suffix: "项",
    trend: -23.1,
    icon: "alert",
    tone: "pink",
    linkTo: "/products/listing-inventory",
  },
  {
    id: "mock-orders",
    label: "模拟订单数",
    value: 1247,
    suffix: "单",
    trend: 8.3,
    icon: "trend",
    tone: "blue",
    linkTo: "/orders",
  },
  {
    id: "pending-sessions",
    label: "待处理客服会话",
    value: 23,
    suffix: "条",
    trend: -5.2,
    icon: "message",
    tone: "purple",
    linkTo: "/customer-service/conversations",
  },
  {
    id: "pending-tasks",
    label: "待确认任务",
    value: 15,
    suffix: "项",
    trend: 0,
    icon: "check",
    tone: "green",
    linkTo: "/tasks",
  },
]

// ---------- 趋势图表数据 ----------

export const trendDatasets: Record<string, TrendDataset> = {
  funnel: {
    categories: ["市场商品", "选品候选", "上架草稿", "模拟上架"],
    series: [
      { name: "商品数量", data: [1280, 320, 86, 42], color: "blue" },
    ],
  },
  orders: {
    categories: ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
    series: [
      { name: "本周", data: [182, 195, 210, 178, 203, 156, 123], color: "blue" },
      { name: "上周", data: [168, 177, 192, 165, 188, 142, 108], color: "pink" },
    ],
  },
  popularity: {
    categories: ["无线耳机", "折叠支架", "收纳包", "充电器", "数据线", "手机壳"],
    series: [
      { name: "浏览量", data: [2840, 1920, 1560, 2130, 980, 1350], color: "blue" },
      { name: "加购量", data: [680, 520, 410, 590, 260, 370], color: "pink" },
    ],
  },
  sentiment: {
    categories: ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
    series: [
      { name: "正面", data: [45, 52, 48, 55, 50, 42, 46], color: "green" },
      { name: "中性", data: [18, 15, 20, 17, 16, 22, 19], color: "blue" },
      { name: "负面", data: [8, 6, 9, 5, 10, 7, 6], color: "pink" },
    ],
  },
  service: {
    categories: ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
    series: [
      { name: "物流查询", data: [28, 32, 25, 30, 35, 18, 15], color: "blue" },
      { name: "商品咨询", data: [22, 19, 24, 20, 26, 14, 12], color: "purple" },
      { name: "售后投诉", data: [8, 10, 7, 12, 9, 5, 4], color: "pink" },
    ],
  },
}

// ---------- 异常提醒 & 今日待办 ----------

export const alertItems: AlertItem[] = [
  {
    id: "alert-1",
    type: "danger",
    title: "低库存预警",
    description: "折叠支架 (B07) 库存低于安全阈值，预计 3 天内断货",
    linkTo: "/products/listing-inventory",
    linkLabel: "前往补货",
    timestamp: "10 分钟前",
  },
  {
    id: "alert-2",
    type: "danger",
    title: "高风险客服消息",
    description: "无线耳机 (A12) 连续 3 条差评，买家情绪负面",
    linkTo: "/customer-service/conversations",
    linkLabel: "查看会话",
    timestamp: "28 分钟前",
  },
  {
    id: "alert-3",
    type: "warning",
    title: "待审批确认任务",
    description: "收纳包 (C03) 商品描述更新待确认，已排队 2 小时",
    linkTo: "/tasks",
    linkLabel: "立即处理",
    timestamp: "2 小时前",
  },
  {
    id: "alert-4",
    type: "info",
    title: "物流异常提醒",
    description: "3 笔订单物流状态超过 48 小时未更新",
    linkTo: "/orders",
    linkLabel: "查看订单",
    timestamp: "3 小时前",
  },
]

// ---------- 最近动态 ----------

export const recentActivities: RecentActivity[] = [
  {
    id: "act-1",
    type: "task",
    action: "AI 生成",
    target: "无线耳机商品描述优化建议",
    status: "completed",
    timestamp: "5 分钟前",
  },
  {
    id: "act-2",
    type: "system",
    action: "数据同步",
    target: "Shopee 模拟市场数据更新完成",
    status: "completed",
    timestamp: "12 分钟前",
  },
  {
    id: "act-3",
    type: "task",
    action: "任务确认",
    target: "折叠支架库存补货计划",
    status: "pending",
    timestamp: "28 分钟前",
  },
  {
    id: "act-4",
    type: "system",
    action: "模拟上架",
    target: "3 款新品已同步至模拟店铺",
    status: "completed",
    timestamp: "45 分钟前",
  },
  {
    id: "act-5",
    type: "task",
    action: "AI 分析",
    target: "近 7 日评论情绪报告生成完毕",
    status: "completed",
    timestamp: "1 小时前",
  },
  {
    id: "act-6",
    type: "system",
    action: "状态检测",
    target: "后端模拟服务健康检查通过",
    status: "completed",
    timestamp: "1 小时前",
  },
  {
    id: "act-7",
    type: "task",
    action: "客服接管",
    target: "#TK-1034 买家要求人工回复",
    status: "processing",
    timestamp: "1.5 小时前",
  },
]
