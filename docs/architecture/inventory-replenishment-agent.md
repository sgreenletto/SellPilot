# 库存健康与补货决策工作流

## 边界

`inventory_replenishment` 是成员二范围内的只读分析工作流。它读取指定 Mock
店铺的商品、SKU、库存、订单和订单明细，返回可解释的补货建议；当前不会修改
库存，也不会调用真实 Shopee。

工作流复用统一 `TaskWorkflowRuntime`，并通过
`analyze_inventory_replenishment` 只读 Tool 调用
`ReplenishmentService`。Tool 不直接访问 SQL，数据库查询集中在
`ReplenishmentRepository`。

## 输入

- `shop_external_id`：店铺外部编号，例如 `SHOP001`。
- `analysis_days`：销量统计窗口，默认 30 天。
- `lead_time_days`：采购或运输提前期，默认 14 天。
- `safety_factor`：需求安全系数，默认 1.20。
- `only_replenishment`：是否只返回建议补货量大于 0 的 SKU。

## 确定性计算

```text
日均销量 = 时间窗内非取消订单销量 / analysis_days
需求目标 = ceil(日均销量 × lead_time_days × safety_factor)
目标库存 = 需求目标
建议补货量 = max(目标库存 - 当前可用库存, 0)
可售天数 = 当前可用库存 / 日均销量
```

数据库安全库存作为预警阈值和复核证据，不会被直接当作必须补到的目标。没有
销量时，可售天数返回 `null`，不会伪造无限天数。风险等级根据可售天数和
补货缺口确定。结果包含公式版本、汇总、逐 SKU 证据与
`is_mock_data` 标识。

## 调用

使用已有任务 API 创建并执行：

```json
{
  "workflow_name": "inventory_replenishment",
  "workflow_input": {
    "shop_external_id": "SHOP001",
    "analysis_days": 30,
    "lead_time_days": 14,
    "safety_factor": "1.20",
    "only_replenishment": true
  }
}
```

创建任务后调用统一任务运行接口。结构化分析结果保存在任务的 `result` 字段。
后续若增加库存调整，必须另建写 Tool，并经过待确认任务和平台适配器执行。
