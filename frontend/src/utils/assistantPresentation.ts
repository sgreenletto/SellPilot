import type { AssistantAvailability, AssistantIntent, AssistantPlan } from "@/api/assistant";
import type { TaskStatus, ToolRiskLevel } from "@/types/contracts";
import {
  formatCategoryName,
  formatCapabilityName,
  formatRiskLevel,
  formatSiteName,
  formatTaskNode,
  formatTaskStatus,
  formatWorkflowName,
} from "@/utils/displayLabels";

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

const stepSummaries: Record<string, string> = {
  search_market_products: "按照站点、类目和价格条件查询真实导入的市场候选商品。",
  select_selection_candidates: "检查是否存在可评分候选；没有数据时返回明确提示。",
  score_product_opportunity: "根据站点与筛选条件评估候选商品机会。",
  finish_selection_success: "整理候选排序、评分依据和数据来源。",
  finish_selection_no_data: "说明当前数据集没有匹配候选。",
  analyze_product_reviews: "分析指定商品的评论、情绪和用户痛点。",
  select_improvement_source: "根据商品编号或已有评论分析编号选择数据来源。",
  analyze_reviews_for_improvement: "读取真实商品评论并生成可追溯的评论分析。",
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
  validate_content_quality: "核验商品事实、完整性、本地化和合规检查结果。",
  finish_content_generation: "整理最终文案和有界质量检查记录。",
  search_knowledge: "按照用户问题检索现有知识库并返回来源。",
  get_customer_conversation: "读取会话和关联订单、商品的上下文。",
  classify_customer_request: "识别问题类型、风险等级和是否需要人工处理。",
  select_customer_branch: "根据问题类型选择知识、订单、物流、商品或人工分支。",
  record_customer_handoff: "记录高风险请求需要转交人工客服。",
  search_customer_knowledge: "检索可引用的商品或店铺政策依据。",
  get_customer_order: "读取客服会话关联的真实订单信息。",
  get_customer_logistics: "读取客服会话关联的真实物流信息。",
  get_customer_product: "读取客服会话关联的商品事实。",
  draft_customer_reply: "只根据已查询到的可靠依据生成回复草稿。",
  select_customer_send: "判断仅返回草稿还是进入模拟发送确认。",
  mock_send_customer_reply: "经用户确认后向 Mock 会话写入一条模拟回复。",
  finish_customer_reply: "整理回复建议、风险和引用依据。",
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
  category_query: "商品类目",
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
  buyer_message: "买家问题",
  simulate_send: "模拟发送",
  max_attempts: "最大检查轮次",
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
  pending: formatTaskStatus("pending"),
  running: formatTaskStatus("running"),
  waiting_confirmation: formatTaskStatus("waiting_confirmation"),
  succeeded: formatTaskStatus("succeeded"),
  failed: formatTaskStatus("failed"),
  cancelled: formatTaskStatus("cancelled"),
};

export const riskLabels: Record<ToolRiskLevel, string> = {
  read: formatRiskLevel("read"),
  write: formatRiskLevel("write"),
  high_risk: formatRiskLevel("high_risk"),
};

export function intentLabel(intent: AssistantIntent): string {
  return intentLabels[intent];
}

export function capabilityLabel(capability: string | null): string {
  if (!capability) return "未匹配";
  return intentLabels[capability as AssistantIntent] ?? formatCapabilityName(capability);
}

export function workflowLabel(workflow: string | null | undefined): string {
  if (!workflow) return "未选择";
  return formatWorkflowName(workflow);
}

export function stepLabel(step: string): string {
  return formatTaskNode(step);
}

export function stepSummary(step: string, fallback: string): string {
  return (
    stepSummaries[step] ??
    (fallback && /[\u3400-\u9fff]/u.test(fallback) ? fallback : `执行“${stepLabel(step)}”步骤。`)
  );
}

export function parameterLabel(parameter: string): string {
  return parameterLabels[parameter] ?? "其他参数";
}

export function displayParameterValue(parameter: string, value: unknown): string {
  if (typeof value === "string") {
    const translated = valueLabels[value];
    return translated ?? value;
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
  return valueLabels[status] ?? formatTaskStatus(status);
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
  if (
    lowered.includes("external service is unavailable") ||
    lowered.includes("provider is unavailable")
  )
    return "内容生成服务暂时不可用，请稍后重试。";
  if (lowered.includes("permission") || lowered.includes("forbidden"))
    return "当前账号无权访问该任务。";
  if (/[\u3400-\u9fff]/u.test(message)) return message;
  return "执行过程中发生错误，请稍后重试。";
}

export function localizedTaskFailure(
  errorCode: string | null | undefined,
  message: string | null | undefined,
  requestId: string | null | undefined,
): string {
  const safeMessage =
    errorCode === "TASK_STATE_TOO_LARGE"
      ? "任务结果超过安全大小限制，请缩小查询范围后重试。"
      : errorCode === "SELECTION_NO_CANDIDATES"
        ? "当前数据中没有匹配的候选商品，请调整站点或商品类目。"
        : localizedErrorMessage(message);
  return requestId ? `${safeMessage} 错误编号：${requestId}` : safeMessage;
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
  return translated ?? raw;
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
    const candidateSearch = asRecord(source.candidate_search) ?? {};
    const filters = asRecord(candidateSearch.normalized_filters) ?? {};
    const site = formatSiteName(asString(filters.site));
    const categoryId = asString(filters.category_id);
    const categoryQuery = asString(filters.category_query);
    const category = categoryId
      ? formatCategoryName(categoryId)
      : categoryQuery
        ? categoryQuery
        : "全站类目";
    const noData = source.no_data === true;
    if (noData) {
      return {
        summary: asString(source.message, "当前数据中没有匹配的候选商品，请调整站点或商品类目。"),
        metrics: [
          { label: "匹配候选", value: "0" },
          { label: "查询站点", value: site },
          { label: "查询类目", value: category },
        ],
        items: [],
      };
    }
    const analysis = asRecord(source.analysis) ?? source;
    const results = asRecords(analysis.results);
    const ranked = asCount(analysis.ranked_count, results.length);
    const total = asCount(analysis.total_candidates, ranked);
    return {
      summary: `智能选品分析已完成，共评估 ${total} 个候选商品，其中 ${ranked} 个进入排序结果。`,
      metrics: [
        { label: "匹配候选", value: String(asCount(candidateSearch.matched_count, total)) },
        { label: "参与评分", value: String(total) },
        { label: "排序结果", value: String(ranked) },
        { label: "查询站点", value: site },
        { label: "查询类目", value: category },
        {
          label: "数据来源",
          value: candidateSearch.is_mock_data === true ? "模拟市场数据" : "市场数据",
        },
      ],
      items: results.slice(0, 8).map((item, index) => ({
        id: asString(item.id, `selection-${index}`),
        title: asString(item.title, asString(item.product_id, "候选商品")),
        subtitle: `排名 ${asString(item.rank, String(index + 1))}，机会总分 ${asString(item.total_score, "—")}`,
        meta: [
          `商品编号：${asString(item.product_id, "—")}`,
          `预估利润率：${asString(asRecord(item.profit)?.margin, "—")}`,
          `数据完整度：${asString(item.data_completeness, "—")}`,
          `站点：${formatSiteName(asString(item.site))}`,
          `数据来源：${item.is_mock_data === true ? "模拟市场数据" : "市场数据"}`,
          Array.isArray(item.risk_warnings) && item.risk_warnings.length > 0
            ? "风险：部分评分数据不完整或未达到筛选条件"
            : "风险：未发现额外数据风险",
        ],
      })),
    };
  }

  if (workflowName === "review_analysis") {
    const analysis = asRecord(source.analysis) ?? source;
    const painPoints = asRecords(analysis.pain_points);
    const topics = asRecords(analysis.topics);
    const quality = asRecord(analysis.quality) ?? {};
    const sentiment = asRecord(analysis.sentiment) ?? {};
    const reviewCount = asCount(quality.included_count, 0);
    if (analysis.no_data === true) {
      return {
        summary: `商品 ${asString(analysis.product_id, "—")} 没有足够评论数据，未生成推断性结论。`,
        metrics: [{ label: "有效评论", value: String(reviewCount) }],
        items: [],
      };
    }
    return {
      summary: `商品 ${asString(analysis.product_id, "—")} 的 ${reviewCount} 条有效评论分析已完成，识别到 ${topics.length} 个主题和 ${painPoints.length} 个主要痛点。`,
      metrics: [
        { label: "有效评论", value: String(reviewCount) },
        {
          label: "正向 / 中性 / 负向",
          value: `${asCount(sentiment.positive, 0)} / ${asCount(sentiment.neutral, 0)} / ${asCount(sentiment.negative, 0)}`,
        },
        { label: "主要痛点", value: String(painPoints.length) },
      ],
      items: painPoints.slice(0, 8).map((item, index) => ({
        id: asString(item.pain_point, `pain-point-${index}`),
        title: asString(item.pain_point, "评论痛点"),
        subtitle: asString(asRecord(asRecords(item.evidence)[0])?.translated_content),
        meta: [
          `负向评论：${asString(item.negative_count, "0")}`,
          `严重度：${asString(item.severity, "—")}`,
        ],
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

  if (workflowName === "content_generation") {
    const generation = asRecord(source.generation) ?? {};
    const generated = asRecord(generation.result) ?? {};
    const content = asRecord(generated.content) ?? {};
    const compliance = asRecord(source.compliance) ?? {};
    const loop = asRecord(source.loop) ?? {};
    const bullets = Array.isArray(content.bullet_points)
      ? content.bullet_points.map((item) => asString(item)).filter(Boolean)
      : [];
    const faq = asRecords(content.faq);
    return {
      summary: `已根据商品 ${asString(generation.product_id, "—")} 的真实资料生成${labelValue(generation.target_language)}文案，事实与合规检查${compliance.passed === true ? "已通过" : "未通过"}。`,
      metrics: [
        {
          label: "检查轮次",
          value: `${asCount(loop.attempts, 0)} / ${asCount(loop.max_attempts, 3)}`,
        },
        { label: "合规检查", value: compliance.passed === true ? "已通过" : "未通过" },
      ],
      items: [
        {
          id: "generated-title",
          title: asString(content.title, "生成标题"),
          subtitle: asString(content.description),
          meta: bullets.slice(0, 5),
        },
        ...faq.slice(0, 3).map((item, index) => ({
          id: `faq-${index}`,
          title: asString(item.question, `FAQ ${index + 1}`),
          subtitle: asString(item.answer),
          meta: [],
        })),
      ],
    };
  }

  if (workflowName === "knowledge_query") {
    const sources = asRecords(source.sources);
    if (source.no_reliable_source === true || sources.length === 0) {
      return {
        summary: "当前知识库中没有找到可靠依据。",
        metrics: [{ label: "可靠来源", value: "0" }],
        items: [],
      };
    }
    return {
      summary: asString(source.answer, "已找到可靠知识依据。"),
      metrics: [{ label: "可靠来源", value: String(sources.length) }],
      items: sources.slice(0, 6).map((item, index) => ({
        id: asString(item.document_id, `source-${index}`),
        title: asString(item.source_doc, "知识来源"),
        subtitle: asString(item.fragment),
        meta: [
          `相关度：${asString(item.score, "—")}`,
          `语言：${labelValue(item.language)}`,
          asString(item.updated_at),
        ].filter(Boolean),
      })),
    };
  }

  if (workflowName === "customer_service_reply") {
    const draft = asRecord(source.draft) ?? {};
    const classification = asRecord(source.classification) ?? {};
    const basis = asRecords(draft.basis);
    const requiresHuman = draft.requires_human === true;
    return {
      summary: asString(
        draft.reply,
        requiresHuman ? "该请求需要转交人工客服处理。" : "已生成客服回复建议。",
      ),
      metrics: [
        { label: "风险等级", value: labelValue(draft.risk_level ?? classification.risk_level) },
        { label: "处理方式", value: requiresHuman ? "转交人工" : "回复草稿" },
        {
          label: "发送状态",
          value: source.simulated_send ? "已模拟发送" : "未发送",
        },
      ],
      items: basis.slice(0, 6).map((item, index) => ({
        id: asString(item.document_id, asString(item.order_id, `basis-${index}`)),
        title:
          item.type === "knowledge"
            ? "知识库依据"
            : item.type === "logistics"
              ? "物流依据"
              : item.type === "order"
                ? "订单依据"
                : "商品依据",
        subtitle: asString(item.source, asString(item.product_id, asString(item.order_id))),
        meta: [],
      })),
    };
  }

  return {
    summary: "任务已完成，以下内容来自本次真实任务结果。",
    metrics: primitiveMetrics(source),
    items: [],
  };
}
