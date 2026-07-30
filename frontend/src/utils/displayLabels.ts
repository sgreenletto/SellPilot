const taskStatusLabels: Record<string, string> = {
  pending: "待执行",
  running: "执行中",
  paused: "已暂停",
  waiting_confirmation: "等待确认",
  confirmed: "已确认",
  executing: "执行中",
  succeeded: "已完成",
  completed: "已完成",
  failed: "执行失败",
  cancelled: "已取消",
  canceled: "已取消",
  rejected: "已拒绝",
  skipped: "已跳过",
  blocked: "已阻止",
  timed_out: "执行超时",
};

const workflowLabels: Record<string, string> = {
  diagnostic: "运行诊断",
  system_health_check: "系统健康检查",
  selection: "智能选品分析",
  review_analysis: "评论分析",
  product_improvement: "产品改良",
  content_generation: "多语言内容生成",
  knowledge_query: "知识库检索",
  customer_service_reply: "客服回复建议",
  inventory_replenishment: "库存补货建议",
  low_stock_check: "低库存检查",
  order_query: "订单查询",
  logistics_query: "物流查询",
};

const taskTypeLabels: Record<string, string> = {
  diagnostic: "诊断任务",
  data_import: "数据导入",
  selection: "智能选品",
  selection_analysis: "智能选品分析",
  review_analysis: "评论分析",
  product_improvement: "产品改良",
  content_generation: "多语言内容生成",
  platform_operation: "平台操作",
  knowledge_ingestion: "知识导入",
  customer_service: "客服任务",
  customer_service_reply: "客服回复建议",
  report_generation: "报告生成",
  replenishment: "库存补货",
  inventory_replenishment: "库存补货建议",
  low_stock_check: "低库存检查",
  order_query: "订单查询",
  logistics_query: "物流查询",
  knowledge_query: "知识库检索",
  assistant: "助手任务",
  analysis: "分析任务",
  workflow: "工作流任务",
};

const taskNodeLabels: Record<string, string> = {
  diagnostic: "完成运行诊断",
  system_health: "检查系统健康状态",
  search_market_products: "查询市场候选商品",
  select_selection_candidates: "检查候选商品",
  score_product_opportunity: "评估商品机会",
  finish_selection_success: "完成选品分析",
  finish_selection_no_data: "返回无候选结果",
  analyze_product_reviews: "分析商品评论",
  select_improvement_source: "选择改良数据来源",
  analyze_reviews_for_improvement: "分析评论证据",
  generate_product_improvement_plan: "生成产品改良建议",
  generate_localized_listing: "生成多语言商品内容",
  check_listing_compliance: "检查商品内容合规性",
  validate_content_quality: "核验内容质量",
  finish_content_generation: "完成内容生成",
  search_knowledge: "检索知识库",
  get_customer_conversation: "读取客服会话",
  classify_customer_request: "识别问题与风险",
  select_customer_branch: "选择客服处理分支",
  record_customer_handoff: "记录人工转交",
  search_customer_knowledge: "查询政策知识",
  get_customer_order: "查询关联订单",
  get_customer_logistics: "查询关联物流",
  get_customer_product: "查询关联商品",
  draft_customer_reply: "生成客服回复建议",
  select_customer_send: "判断模拟发送",
  mock_send_customer_reply: "确认后模拟发送",
  finish_customer_reply: "完成客服回复建议",
  list_low_stock: "检查低库存商品",
  select_order_query: "选择订单查询方式",
  get_order: "查询单个订单",
  list_orders: "查询订单列表",
  finish_order_query: "完成订单查询",
  get_order_logistics: "查询订单物流",
  analyze_inventory_replenishment: "分析库存补货需求",
  publish: "发布商品",
};

const confirmationStatusLabels: Record<string, string> = {
  pending: "待确认",
  confirmed: "已确认",
  executing: "执行中",
  succeeded: "已完成",
  failed: "执行失败",
  cancelled: "已取消",
  canceled: "已取消",
  rejected: "已拒绝",
};

const riskLevelLabels: Record<string, string> = {
  read: "只读",
  write: "写入",
  high_risk: "高风险",
  low: "低风险",
  medium: "中风险",
  high: "高风险",
  critical: "紧急风险",
  warning: "需关注",
  healthy: "正常",
};

const toolLabels: Record<string, string> = {
  system_health: "系统健康检查",
  list_products: "查询商品列表",
  get_product: "查询商品详情",
  list_product_skus: "查询商品 SKU",
  list_inventory: "查询库存",
  list_low_stock: "查询低库存",
  list_orders: "查询订单列表",
  get_order: "查询订单详情",
  get_order_logistics: "查询订单物流",
  search_market_products: "查询市场候选商品",
  calculate_product_profit: "计算商品利润",
  score_product_opportunity: "评估商品机会",
  compare_products: "比较候选商品",
  export_product_analysis_report: "导出商品分析报告",
  get_product_reviews: "查询商品评论",
  analyze_product_reviews: "分析商品评论",
  generate_product_improvement_plan: "生成产品改良建议",
  generate_localized_listing: "生成多语言商品内容",
  check_listing_compliance: "检查商品内容合规性",
  search_knowledge: "检索知识库",
  get_customer_conversation: "读取客服会话",
  classify_customer_request: "识别客服问题与风险",
  draft_customer_reply: "生成客服回复建议",
  mock_send_customer_reply: "模拟发送客服回复",
  analyze_inventory_replenishment: "分析库存补货需求",
  mock_publish: "模拟发布商品",
};

const operationTypeLabels: Record<string, string> = {
  "tool.execute": "执行工具",
  "commerce.publish_product": "发布商品",
  "commerce.unpublish_product": "下架商品",
  "commerce.update_price": "更新商品价格",
  "commerce.update_inventory": "调整库存",
  "commerce.save_product_draft": "保存商品草稿",
  "commerce.import_products": "导入商品",
  "commerce.add_selection_candidate": "加入选品候选",
  "commerce.remove_selection_candidate": "移除选品候选",
  "content_generation.save_draft": "保存内容草稿",
  "content_generation.restore_version": "恢复内容版本",
  "product_improvement.create_content_draft": "创建改良内容草稿",
  "product_improvement.revise_content_draft": "修订改良内容草稿",
  "product_improvement.clear_draft_history": "清空改良草稿历史",
  "product_translation.translate": "翻译商品内容",
  create_prompt_version: "创建提示词版本",
  set_prompt_status: "更新提示词状态",
  confirmation_requested: "请求确认",
  confirmation_confirmed: "确认执行",
  confirmation_cancelled: "取消确认",
  task_created: "创建任务",
  task_started: "开始任务",
  task_succeeded: "完成任务",
  task_failed: "任务失败",
  tool_call_started: "开始调用工具",
  tool_call_succeeded: "工具调用完成",
  tool_call_failed: "工具调用失败",
};

const capabilityLabels: Record<string, string> = {
  selection_analysis: "智能选品分析",
  review_analysis: "评论分析",
  product_improvement: "产品改良",
  inventory_replenishment: "库存补货建议",
  low_stock_check: "低库存检查",
  order_query: "订单查询",
  logistics_query: "物流查询",
  content_generation: "多语言内容生成",
  knowledge_query: "知识库检索",
  customer_service_reply: "客服回复建议",
  unknown: "未识别请求",
};

const platformModeLabels: Record<string, string> = {
  mock: "模拟模式",
  real: "真实平台模式",
  real_stub: "真实平台接口未配置",
};

const siteLabels: Record<string, string> = {
  sg: "新加坡站",
  Singapore: "新加坡站",
  my: "马来西亚站",
  Malaysia: "马来西亚站",
  ph: "菲律宾站",
  Philippines: "菲律宾站",
  th: "泰国站",
  Thailand: "泰国站",
  vn: "越南站",
  Vietnam: "越南站",
  id: "印度尼西亚站",
  Indonesia: "印度尼西亚站",
  tw: "中国台湾站",
  Taiwan: "中国台湾站",
  br: "巴西站",
  Brazil: "巴西站",
};

const categoryLabels: Record<string, string> = {
  CAT001: "手机配件",
  CAT002: "家居用品",
  CAT003: "美妆护理",
  CAT004: "女装",
  CAT005: "男装",
  CAT006: "电脑办公",
  CAT007: "运动户外",
  CAT008: "母婴用品",
};

const dataSourceLabels: Record<string, string> = {
  mock: "模拟数据",
  imported: "导入数据",
  collected: "采集数据",
  generated: "生成数据",
  manual: "手工数据",
  manual_import: "手工导入",
  simulated_experiment: "模拟实验数据",
};

const nodeTypeLabels: Record<string, string> = {
  action: "操作",
  tool: "工具调用",
  branch: "条件分支",
  loop: "循环检查",
  wait: "等待",
  finish: "完成",
};

const taskActionLabels: Record<string, string> = {
  run: "运行",
  resume: "继续",
  retry: "重试",
  rerun: "重新运行",
  cancel: "取消",
};

const businessStatusLabels: Record<string, string> = {
  active: "在售",
  inactive: "已下架",
  draft: "草稿",
  archived: "已归档",
  pending_confirmation: "等待确认",
  published: "已上架",
  unpublished: "已下架",
  publish_failed: "上架失败",
  out_of_stock: "已缺货",
  pending: "待处理",
  paid: "已支付",
  processing: "处理中",
  shipped: "已发货",
  completed: "已完成",
  cancelled: "已取消",
  refunded: "已退款",
  ready_to_ship: "待发货",
  in_transit: "运输中",
  delivered: "已送达",
  exception: "物流异常",
  returned: "已退回",
  pending_pickup: "待揽收",
  picked_up: "已揽收",
  out_for_delivery: "派送中",
  customs_clearance: "清关中",
  requested: "已申请",
  approved: "已批准",
  rejected: "已拒绝",
  open: "处理中",
  pending_reply: "待回复",
  pending_manual: "待人工处理",
  resolved: "已解决",
  closed: "已关闭",
  none: "无",
  low_stock: "库存偏低",
  healthy: "库存正常",
  AVAILABLE: "可执行",
  CONTRACT_ONLY: "仅契约",
  UNAVAILABLE: "暂不可用",
  PROPOSED: "待审查",
  ACCEPTED: "已采纳",
  IGNORED: "已忽略",
};

const customerIntentLabels: Record<string, string> = {
  product_inquiry: "商品咨询",
  order_query: "订单查询",
  logistics_query: "物流查询",
  logistics_delay: "物流延误",
  return_policy: "退货政策",
  refund_request: "退款申请",
  complaint: "投诉",
  cancel_order: "取消订单",
  size_inquiry: "尺寸咨询",
  stock_inquiry: "库存咨询",
  product_recommendation: "商品推荐",
  compensation: "赔付",
  address_change: "修改地址",
  order_change: "修改订单",
  other: "其他问题",
};

const languageLabels: Record<string, string> = {
  en: "英文",
  "zh-CN": "简体中文",
  "zh-TW": "繁体中文",
  ms: "马来语",
  id: "印度尼西亚语",
  th: "泰语",
  vi: "越南语",
  tl: "菲律宾语",
  "pt-BR": "巴西葡萄牙语",
};

const senderTypeLabels: Record<string, string> = {
  buyer: "买家",
  seller: "卖家",
  assistant: "助手",
  agent: "客服",
  system: "系统",
};

const afterSaleTypeLabels: Record<string, string> = {
  refund: "退款",
  return: "退货",
  return_refund: "退货退款",
  return_and_refund: "退货退款",
  refund_only: "仅退款",
  cancellation: "取消订单",
  compensation: "赔付",
};

const afterSaleReasonLabels: Record<string, string> = {
  changed_mind: "改变购买意愿",
  damaged: "商品损坏",
  quality_issue: "质量问题",
  size_issue: "尺寸问题",
  wrong_item: "商品发错",
  late_delivery: "配送延误",
  not_as_described: "与描述不符",
};

const logisticsTextLabels: Record<string, string> = {
  "Shipment information received": "已收到发货信息",
  "Parcel picked up by carrier": "承运商已揽收包裹",
  "Parcel is moving to destination": "包裹正在运往目的地",
  "Parcel delivered to the simulated buyer": "包裹已送达模拟买家",
  "Courier is delivering the parcel": "快递员正在派送",
  "Customs processing completed": "清关处理已完成",
  "Shipment label created": "已创建物流面单",
  "Parcel packed and awaiting carrier pickup": "包裹已打包，等待承运商揽收",
  "Temporary routing exception; manual review required": "运输路线临时异常，需要人工处理",
  "Shenzhen Demo Warehouse": "深圳模拟仓库",
  "Shenzhen Sorting Center": "深圳分拨中心",
  "Regional Transit Hub": "区域中转中心",
  Singapore: "新加坡",
  "Kuala Lumpur Delivery Hub": "吉隆坡配送中心",
  "Kuala Lumpur": "吉隆坡",
  "Manila Customs": "马尼拉海关",
  "Manila Delivery Hub": "马尼拉配送中心",
  Manila: "马尼拉",
  "Bangkok Customs": "曼谷海关",
  Bangkok: "曼谷",
  "Ho Chi Minh City Customs": "胡志明市海关",
  "Ho Chi Minh City": "胡志明市",
  "Jakarta Delivery Hub": "雅加达配送中心",
  Jakarta: "雅加达",
  "Singapore Customs": "新加坡海关",
  "Bangkok Delivery Hub": "曼谷配送中心",
  "Jakarta Customs": "雅加达海关",
  "Singapore Delivery Hub": "新加坡配送中心",
  "Kuala Lumpur Customs": "吉隆坡海关",
  "Ho Chi Minh City Delivery Hub": "胡志明市配送中心",
};

function labelFrom(
  labels: Record<string, string>,
  value: string | null | undefined,
  fallback: string,
) {
  if (!value) return fallback;
  return labels[value] ?? fallback;
}

export function formatTaskStatus(value: string | null | undefined): string {
  return labelFrom(taskStatusLabels, value, "未知状态");
}

export function formatWorkflowName(value: string | null | undefined): string {
  return labelFrom(workflowLabels, value, "未知工作流");
}

export function formatTaskType(value: string | null | undefined): string {
  return labelFrom(taskTypeLabels, value, "未知任务类型");
}

export function formatTaskNode(value: string | null | undefined): string {
  return labelFrom(taskNodeLabels, value, "未知节点");
}

export function formatConfirmationStatus(value: string | null | undefined): string {
  return labelFrom(confirmationStatusLabels, value, "未知确认状态");
}

export function formatRiskLevel(value: string | null | undefined): string {
  return labelFrom(riskLevelLabels, value, "未知风险");
}

export function formatToolName(value: string | null | undefined): string {
  return labelFrom(toolLabels, value, "未知工具");
}

export function formatOperationType(value: string | null | undefined): string {
  return labelFrom(operationTypeLabels, value, "未知操作");
}

export function formatCapabilityName(value: string | null | undefined): string {
  return labelFrom(capabilityLabels, value, "未知能力");
}

export function formatPlatformMode(value: string | null | undefined): string {
  return labelFrom(platformModeLabels, value, "未知平台模式");
}

export function formatSiteName(value: string | null | undefined): string {
  return labelFrom(siteLabels, value, "未知站点");
}

export function formatCategoryName(value: string | null | undefined): string {
  return labelFrom(categoryLabels, value, "未知类目");
}

export function formatDataSource(value: string | null | undefined): string {
  return labelFrom(dataSourceLabels, value, "未知数据来源");
}

export function formatTaskNodeType(value: string | null | undefined): string {
  return labelFrom(nodeTypeLabels, value, "未知节点类型");
}

export function formatTaskAction(value: string | null | undefined): string {
  return labelFrom(taskActionLabels, value, "未知操作");
}

export function formatBusinessStatus(value: string | null | undefined): string {
  return labelFrom(businessStatusLabels, value, "未知状态");
}

export function formatCustomerIntent(value: string | null | undefined): string {
  return labelFrom(customerIntentLabels, value, "其他问题");
}

export function formatLanguageName(value: string | null | undefined): string {
  return labelFrom(languageLabels, value, "未知语言");
}

export function formatSenderType(value: string | null | undefined): string {
  return labelFrom(senderTypeLabels, value, "未知发送方");
}

export function formatAfterSaleType(value: string | null | undefined): string {
  return labelFrom(afterSaleTypeLabels, value, "其他售后");
}

export function formatAfterSaleReason(value: string | null | undefined): string {
  return labelFrom(afterSaleReasonLabels, value, "其他原因");
}

export function formatLogisticsText(value: string | null | undefined): string {
  if (!value) return "暂无信息";
  return logisticsTextLabels[value] ?? value;
}

export const DISPLAY_LABEL_VALUES = {
  taskStatuses: taskStatusLabels,
  workflows: workflowLabels,
  taskTypes: taskTypeLabels,
  taskNodes: taskNodeLabels,
  tools: toolLabels,
} as const;
