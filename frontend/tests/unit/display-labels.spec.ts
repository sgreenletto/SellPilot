import { describe, expect, it } from "vitest";

import {
  DISPLAY_LABEL_VALUES,
  formatCapabilityName,
  formatConfirmationStatus,
  formatOperationType,
  formatPlatformMode,
  formatRiskLevel,
  formatTaskNode,
  formatTaskStatus,
  formatTaskType,
  formatToolName,
  formatWorkflowName,
} from "@/utils/displayLabels";

describe("统一展示映射", () => {
  it("将任务状态、工作流和任务类型显示为中文", () => {
    expect(formatTaskStatus("succeeded")).toBe("已完成");
    expect(formatWorkflowName("review_analysis")).toBe("评论分析");
    expect(formatTaskType("platform_operation")).toBe("平台操作");
    expect(formatWorkflowName("low_stock_check")).toBe("低库存检查");
    expect(formatWorkflowName("logistics_query")).toBe("物流查询");
  });

  it("覆盖后端注册的全部工作流、任务类型和任务状态", () => {
    expect(Object.keys(DISPLAY_LABEL_VALUES.workflows).sort()).toEqual(
      [
        "content_generation",
        "customer_service_reply",
        "diagnostic",
        "inventory_replenishment",
        "knowledge_query",
        "logistics_query",
        "low_stock_check",
        "order_query",
        "product_improvement",
        "review_analysis",
        "selection",
        "system_health_check",
      ].sort(),
    );
    expect(Object.keys(DISPLAY_LABEL_VALUES.taskTypes)).toEqual(
      expect.arrayContaining([
        "diagnostic",
        "data_import",
        "selection",
        "review_analysis",
        "product_improvement",
        "content_generation",
        "platform_operation",
        "knowledge_ingestion",
        "customer_service",
        "report_generation",
        "replenishment",
      ]),
    );
    for (const status of [
      "pending",
      "running",
      "waiting_confirmation",
      "succeeded",
      "failed",
      "cancelled",
    ]) {
      expect(formatTaskStatus(status)).not.toMatch(/^[a-z_]+$/);
    }
  });

  it("覆盖统一工具注册表中的全部工具", () => {
    expect(Object.keys(DISPLAY_LABEL_VALUES.tools).sort()).toEqual(
      expect.arrayContaining(
        [
          "analyze_inventory_replenishment",
          "analyze_product_reviews",
          "calculate_product_profit",
          "check_listing_compliance",
          "classify_customer_request",
          "compare_products",
          "draft_customer_reply",
          "export_product_analysis_report",
          "generate_localized_listing",
          "generate_product_improvement_plan",
          "get_customer_conversation",
          "get_order",
          "get_order_logistics",
          "get_product",
          "get_product_reviews",
          "list_inventory",
          "list_low_stock",
          "list_orders",
          "list_product_skus",
          "list_products",
          "mock_send_customer_reply",
          "score_product_opportunity",
          "search_knowledge",
          "search_market_products",
          "system_health",
        ].sort(),
      ),
    );
  });

  it("统一处理节点、确认、风险、操作、能力和平台模式", () => {
    expect(formatTaskNode("analyze_product_reviews")).toBe("分析商品评论");
    expect(formatConfirmationStatus("pending")).toBe("待确认");
    expect(formatRiskLevel("high_risk")).toBe("高风险");
    expect(formatToolName("get_order")).toBe("查询订单详情");
    expect(formatOperationType("commerce.update_inventory")).toBe("调整库存");
    expect(formatCapabilityName("selection_analysis")).toBe("智能选品分析");
    expect(formatPlatformMode("mock")).toBe("模拟模式");
  });

  it("未知稳定值不会直接暴露英文蛇形标识", () => {
    expect(formatTaskStatus("new_backend_status")).toBe("未知状态");
    expect(formatWorkflowName("new_backend_workflow")).toBe("未知工作流");
    expect(formatTaskType("new_backend_type")).toBe("未知任务类型");
    expect(formatTaskNode("new_backend_node")).toBe("未知节点");
    expect(formatToolName("new_backend_tool")).toBe("未知工具");
  });
});
