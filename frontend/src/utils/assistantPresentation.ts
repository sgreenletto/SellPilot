import type { AssistantAvailability, AssistantIntent, AssistantPlan } from "@/api/assistant";
import type { TaskStatus, ToolRiskLevel } from "@/types/contracts";

const intentLabels: Record<AssistantIntent, string> = {
  selection_analysis: "智能选品分析",
  review_analysis: "商品评论分析",
  product_improvement: "产品改良建议",
  content_generation: "多语言内容生成",
  inventory_replenishment: "库存补货建议",
  low_stock_check: "低库存检查",
  order_query: "订单查询",
  logistics_query: "物流查询",
  knowledge_query: "知识库检索",
  customer_service_reply: "客服回复建议",
  unknown: "未识别请求",
};

const workflowLabels: Record<string, string> = {
  selection: "智能选品分析",
  review_analysis: "商品评论分析",
  product_improvement: "产品改良建议",
  inventory_replenishment: "库存补货建议",
  low_stock_check: "低库存检查",
  order_query: "订单查询",
  logistics_query: "物流查询",
};

const stepLabels: Record<string, string> = {
  score_product_opportunity: "评估商品机会",
  analyze_product_reviews: "分析商品评论",
  generate_product_improvement_plan: "生成产品改良建议",
  analyze_inventory_replenishment: "分析库存补货需求",
  list_low_stock: "检查低库存商品",
  select_order_query: "选择订单查询方式",
  get_order: "查询单个订单",
  list_orders: "查询订单列表",
  finish_order_query: "完成订单查询",
  get_order_logistics: "查询订单物流",
  generate_localized_listing: "生成多语言商品内容",
  check_listing_compliance: "检查商品内容合规性",
  knowledge_query: "检索知识库",
  customer_service_reply: "生成客服回复建议",
};

const stepSummaries: Record<string, string> = {
  score_product_opportunity: "根据站点与筛选条件评估候选商品机会。",
  analyze_product_reviews: "分析指定商品的评论、情绪和用户痛点。",
  generate_product_improvement_plan: "根据已有评论分析生成产品改良建议。",
  analyze_inventory_replenishment: "分析库存健康度和近期销量并生成补货建议。",
  list_low_stock: "读取低于库存预警阈值的 SKU。",
  select_order_query: "根据是否提供订单编号，在单个订单查询和订单列表查询之间选择。",
  get_order: "读取指定订单的信息。",
  list_orders: "按照店铺或订单状态查询订单列表。",
  finish_order_query: "整理订单查询结果。",
  get_order_logistics: "读取订单的物流信息和运输节点。",
  generate_localized_listing: "生成目标语言的商品内容。",
  check_listing_compliance: "检查生成内容是否符合平台要求。",
  knowledge_query: "按照用户问题检索知识库。",
  customer_service_reply: "根据会话上下文生成客服回复建议。",
};

const parameterLabels: Record<string, string> = {
  status: "订单状态",
  order_status: "订单状态",
  order_id: "订单编号",
  product_id: "商品编号",
  analysis_id: "评论分析编号",
  session_id: "客服会话编号",
  shop_id: "店铺编号",
  shop_external_id: "店铺编号",
  site: "站点",
  category: "商品类目",
  category_id: "商品类目",
  language: "目标语言",
  target_language: "目标语言",
  query: "检索问题",
  top_k: "返回数量",
  limit: "返回数量",
  analysis_days: "分析周期",
  lead_time_days: "备货周期",
  safety_factor: "安全系数",
  only_replenishment: "仅显示需补货商品",
  risk_preference: "风险偏好",
  min_price: "最低价格",
  max_price: "最高价格",
  min_rating: "最低评分",
  max_rating: "最高评分",
  languages: "评论语言",
};

const valueLabels: Record<string, string> = {
  pending: "待执行",
  paid: "已支付",
  processing: "处理中",
  shipped: "已发货",
  completed: "已完成",
  cancelled: "已取消",
  refunded: "已退款",
  running: "执行中",
  waiting_confirmation: "等待确认",
  succeeded: "已完成",
  failed: "执行失败",
  ready_to_ship: "待发货",
  in_transit: "运输中",
  delivered: "已送达",
  exception: "物流异常",
  returned: "已退回",
  pending_pickup: "待揽收",
  picked_up: "已揽收",
  low_stock: "库存偏低",
  out_of_stock: "已缺货",
  healthy: "库存正常",
  critical: "紧急",
  warning: "需关注",
  high: "高",
  medium: "中",
  low: "低",
  conservative: "稳健",
  balanced: "均衡",
  growth: "增长",
  sg: "新加坡",
  my: "马来西亚",
  ph: "菲律宾",
  th: "泰国",
  vn: "越南",
  id: "印度尼西亚",
  tw: "中国台湾",
  br: "巴西",
  en: "英文",
  "zh-CN": "简体中文",
  "zh-TW": "繁体中文",
  ms: "马来语",
  vi: "越南语",
  tl: "菲律宾语",
  "pt-BR": "巴西葡萄牙语",
  Singapore: "新加坡",
  Malaysia: "马来西亚",
  Philippines: "菲律宾",
  Thailand: "泰国",
  Vietnam: "越南",
  Indonesia: "印度尼西亚",
  Taiwan: "中国台湾",
  Brazil: "巴西",
};

const businessTextLabels: Record<string, string> = {
  Singapore: "新加坡",
  "Shenzhen Demo Warehouse": "深圳模拟仓库",
  "Shenzhen Sorting Center": "深圳分拨中心",
  "Regional Transit Hub": "区域中转中心",
  "Shipment information received": "已收到发货信息",
  "Parcel picked up by carrier": "承运商已揽收包裹",
  "Parcel is moving to destination": "包裹正在运往目的地",
  "Parcel delivered to the simulated buyer": "包裹已送达模拟买家",
};

export const availabilityLabels: Record<AssistantAvailability, string> = {
  available: "可执行",
  contract_only: "仅契约",
  unavailable: "暂不可用",
};

export const taskStatusLabels: Record<TaskStatus, string> = {
  pending: "待执行",
  running: "执行中",
  waiting_confirmation: "等待确认",
  succeeded: "已完成",
  failed: "执行失败",
  cancelled: "已取消",
};

export const riskLabels: Record<ToolRiskLevel, string> = {
  read: "只读",
  write: "写入",
  high_risk: "高风险",
};

export function intentLabel(intent: AssistantIntent): string {
  return intentLabels[intent];
}

export function capabilityLabel(capability: string | null): string {
  if (!capability) return "未匹配";
  return intentLabels[capability as AssistantIntent] ?? capability;
}

export function workflowLabel(workflow: string | null | undefined): string {
  if (!workflow) return "未选择";
  return workflowLabels[workflow] ?? workflow;
}

export function stepLabel(step: string): string {
  return stepLabels[step] ?? step;
}

export function stepSummary(step: string, fallback: string): string {
  return (
    stepSummaries[step] ??
    (fallback && /[\u3400-\u9fff]/u.test(fallback) ? fallback : `执行“${stepLabel(step)}”步骤。`)
  );
}

export function parameterLabel(parameter: string): string {
  return parameterLabels[parameter] ?? parameter;
}

export function displayParameterValue(parameter: string, value: unknown): string {
  if (typeof value === "string") {
    const translated = valueLabels[value];
    return translated ? `${translated}（${value}）` : value;
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  if (Array.isArray(value)) {
    return value.map((item) => displayParameterValue(parameter, item)).join("、");
  }
  if (value === null || value === undefined) {
    return "未提供";
  }
  if (typeof value === "number") {
    return String(value);
  }
  return JSON.stringify(value);
}

export function statusLabel(status: string): string {
  return valueLabels[status] ?? status;
}

export function missingParameterPrompt(parameters: string[]): string {
  if (parameters.length === 1 && parameters[0] === "order_id") {
    return "请提供需要查询的订单编号。";
  }
  if (parameters.length === 1 && parameters[0] === "analysis_id") {
    return "请提供需要生成改良建议的评论分析编号。";
  }
  const labels = parameters.map(parameterLabel);
  return `请补充${labels.join("和")}。`;
}

export function planRiskLabel(plan: AssistantPlan): string {
  return plan.requires_confirmation ? "需要确认" : "只读";
}

export function localizedErrorMessage(message: string | null | undefined): string {
  if (!message) return "执行过程中发生错误，请稍后重试。";
  const lowered = message.toLowerCase();
  if (lowered.includes("not found")) return "没有找到对应的业务数据。";
  if (lowered.includes("timeout") || lowered.includes("timed out")) return "执行超时，请稍后重试。";
  if (lowered.includes("permission") || lowered.includes("forbidden"))
    return "当前账号无权访问该任务。";
  if (/[\u3400-\u9fff]/u.test(message)) return message;
  return "执行过程中发生错误，请稍后重试。";
}

export interface AssistantResultMetric {
  label: string;
  value: string;
}

export interface AssistantResultItem {
  id: string;
  title: string;
  subtitle?: string;
  meta: string[];
}

export interface AssistantResultPresentation {
  summary: string;
  metrics: AssistantResultMetric[];
  items: AssistantResultItem[];
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.map(asRecord).filter((item): item is Record<string, unknown> => item !== null)
    : [];
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" || typeof value === "number" ? String(value) : fallback;
}

function asCount(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function labelValue(value: unknown): string {
  const raw = asString(value, "—");
  const translated = valueLabels[raw];
  return translated ? `${translated}（${raw}）` : raw;
}

function localizedBusinessText(value: unknown, fallback = ""): string {
  const raw = asString(value, fallback);
  return businessTextLabels[raw] ?? raw;
}

function primitiveMetrics(source: Record<string, unknown>): AssistantResultMetric[] {
  return Object.entries(source)
    .filter(([, value]) => ["string", "number", "boolean"].includes(typeof value))
    .slice(0, 4)
    .map(([key, value]) => ({
      label: parameterLabel(key),
      value: displayParameterValue(key, value),
    }));
}

export function presentTaskResult(
  workflowName: string,
  result: Record<string, unknown> | null,
): AssistantResultPresentation {
  const source = result ?? {};

  if (workflowName === "logistics_query") {
    const logistics = asRecord(source.logistics) ?? {};
    const orderId = asString(logistics.order_id, "该订单");
    const location = localizedBusinessText(logistics.latest_location, "暂无最新位置");
    const status = labelValue(logistics.status);
    const tracks = asRecords(logistics.tracks);
    return {
      summary: `订单 ${orderId} 当前运输状态为${status}，最新节点为${location}。`,
      metrics: [
        { label: "物流单号", value: asString(logistics.tracking_number, "—") },
        { label: "承运商", value: asString(logistics.carrier, "—") },
      ],
      items: tracks.slice(0, 5).map((track, index) => ({
        id: asString(track.track_id, `track-${index}`),
        title: localizedBusinessText(track.location, "物流节点"),
        subtitle: localizedBusinessText(track.description),
        meta: [labelValue(track.status), asString(track.event_time)].filter(Boolean),
      })),
    };
  }

  if (workflowName === "order_query") {
    const singleOrder = asRecord(source.order);
    const orders = singleOrder ? [singleOrder] : asRecords(source.orders);
    const count = asCount(source.count, orders.length);
    const mode = source.mode === "single" ? "single" : "list";
    return {
      summary:
        mode === "single" && singleOrder
          ? `已查询到订单 ${asString(singleOrder.order_id)}，当前状态为${labelValue(singleOrder.order_status)}。`
          : `共查询到 ${count} 个符合条件的订单。`,
      metrics: [{ label: "订单数量", value: String(count) }],
      items: orders.slice(0, 8).map((order, index) => ({
        id: asString(order.order_id, `order-${index}`),
        title: asString(order.order_id, "订单"),
        subtitle: labelValue(order.order_status),
        meta: [
          asString(order.site) ? `站点：${labelValue(order.site)}` : "",
          asString(order.total_amount)
            ? `金额：${asString(order.currency)} ${asString(order.total_amount)}`
            : "",
        ].filter(Boolean),
      })),
    };
  }

  if (workflowName === "low_stock_check") {
    const inventory = asRecords(source.inventory);
    const count = asCount(source.count, inventory.length);
    return {
      summary: `当前共有 ${count} 个 SKU 低于库存预警阈值。`,
      metrics: [{ label: "低库存 SKU", value: String(count) }],
      items: inventory.slice(0, 8).map((item, index) => ({
        id: asString(item.inventory_id, `inventory-${index}`),
        title: asString(item.sku_id, "SKU"),
        subtitle: asString(item.product_id),
        meta: [
          `可用库存：${asString(item.available_stock, "0")}`,
          `安全库存：${asString(item.safety_stock, "0")}`,
        ],
      })),
    };
  }

  if (workflowName === "inventory_replenishment") {
    const summary = asRecord(source.summary) ?? {};
    const recommendations = asRecords(source.recommendations);
    const skuCount = asCount(summary.replenishment_skus, recommendations.length);
    const units = asCount(summary.recommended_units, 0);
    return {
      summary: `已为 ${skuCount} 个 SKU 生成补货建议，共建议补充 ${units} 件库存；系统未自动调整库存。`,
      metrics: [
        { label: "建议补货 SKU", value: String(skuCount) },
        { label: "建议补货件数", value: String(units) },
      ],
      items: recommendations.slice(0, 8).map((item, index) => ({
        id: asString(item.sku_id, `recommendation-${index}`),
        title: asString(item.seller_sku, asString(item.sku_id, "SKU")),
        subtitle: asString(item.product_title),
        meta: [
          `建议补货：${asString(item.recommended_quantity, "0")} 件`,
          `风险：${labelValue(item.risk_level)}`,
        ],
      })),
    };
  }

  if (workflowName === "selection") {
    const analysis = asRecord(source.analysis) ?? source;
    const results = asRecords(analysis.results);
    const ranked = asCount(analysis.ranked_count, results.length);
    const total = asCount(analysis.total_candidates, ranked);
    return {
      summary: `智能选品分析已完成，共评估 ${total} 个候选商品，其中 ${ranked} 个进入排序结果。`,
      metrics: [
        { label: "候选商品", value: String(total) },
        { label: "入选商品", value: String(ranked) },
      ],
      items: results.slice(0, 8).map((item, index) => ({
        id: asString(item.id, `selection-${index}`),
        title: asString(item.title, asString(item.product_id, "候选商品")),
        subtitle: `排名 ${asString(item.rank, String(index + 1))}`,
        meta: [`综合得分：${asString(item.total_score, "—")}`, `站点：${labelValue(item.site)}`],
      })),
    };
  }

  if (workflowName === "review_analysis") {
    const analysis = asRecord(source.analysis) ?? source;
    const painPoints = asRecords(analysis.pain_points);
    const topics = asRecords(analysis.topics);
    return {
      summary: `商品 ${asString(analysis.product_id, "—")} 的评论分析已完成，识别到 ${topics.length} 个主题和 ${painPoints.length} 个主要痛点。`,
      metrics: [
        { label: "评论主题", value: String(topics.length) },
        { label: "主要痛点", value: String(painPoints.length) },
      ],
      items: painPoints.slice(0, 8).map((item, index) => ({
        id: asString(item.key, `pain-point-${index}`),
        title: asString(item.label, asString(item.name, "评论痛点")),
        meta: primitiveMetrics(item).map((metric) => `${metric.label}：${metric.value}`),
      })),
    };
  }

  if (workflowName === "product_improvement") {
    const report = asRecord(source.report) ?? source;
    const suggestions = asRecords(report.suggestions);
    return {
      summary: `已生成 ${suggestions.length} 条产品改良建议，请在应用建议前核对证据。`,
      metrics: [{ label: "改良建议", value: String(suggestions.length) }],
      items: suggestions.slice(0, 8).map((item, index) => ({
        id: asString(item.id, `suggestion-${index}`),
        title: asString(item.title, "产品改良建议"),
        subtitle: asString(item.description),
        meta: [
          asString(item.priority) ? `优先级：${asString(item.priority)}` : "",
          asString(item.evidence_count) ? `证据数：${asString(item.evidence_count)}` : "",
        ].filter(Boolean),
      })),
    };
  }

  return {
    summary: "任务已完成，以下内容来自本次真实任务结果。",
    metrics: primitiveMetrics(source),
    items: [],
  };
}
