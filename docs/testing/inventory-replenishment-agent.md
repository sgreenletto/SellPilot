# 库存健康与补货决策验收

## 验收边界

本能力属于成员二的库存运营范围。它读取 PostgreSQL 中的 Mock 店铺、商品、SKU、
库存、订单和订单明细，通过统一 Task/Tool/Workflow Runtime 返回补货建议。
它不负责成员三的选品评分，也不直接修改库存或调用真实 Shopee。

## 计算检查

核心公式：

```text
日均销量 = 分析窗口内非取消订单销量 / 分析天数
目标库存 = ceil(日均销量 × 采购提前期 × 安全系数)
建议补货 = max(目标库存 - 当前可用库存, 0)
```

静态安全库存只作为预警阈值和复核证据，不直接成为补货目标。例如 90 天销量
2 件、可用库存 5 件、静态阈值 15 件时，14 天提前期和 1.2 安全系数得到目标
库存 1 件，建议补货 0 件，并提示复核偏保守的静态阈值。

## 真实 API 联调记录

2026-07-29 使用本地 PostgreSQL、默认演示用户和临时本地后端完成以下链路：

```text
POST /api/v1/auth/login
POST /api/v1/tasks                 workflow_name=inventory_replenishment
POST /api/v1/tasks/{task_id}/run
```

SHOP001、90 天分析周期、30 天提前期、1.5 安全系数的结果：

```text
status: succeeded
analyzed_skus: 40
replenishment_skus: 1
critical_skus: 1
recommended_units: 2
formula_version: replenishment-v1.0.0
is_mock_data: true
```

该记录证明登录、任务持久化、工作流执行、数据库聚合和结构化返回链路可用。

## 页面验收

打开 `/products/listing-inventory`，选择具体店铺后可使用三个预设：

- 日常需求：90 天、14 天提前期、1.2 安全系数。
- 活动备货：90 天、30 天提前期、1.5 安全系数。
- 旺季压力测试：90 天、60 天提前期、2.0 安全系数。

页面应展示分析 SKU 数、建议补货 SKU 数、严重风险、建议总件数，以及逐 SKU
的销量、日均销量、可售天数、目标库存、建议数量、风险和计算依据。切换店铺
后旧结果应清空，避免把一个店铺的建议误认为另一个店铺的数据。

## 自动化检查

```powershell
cd D:\SellPilot\backend
$env:DEBUG='false'
uv run ruff check src/sellpilot/repositories/replenishment.py `
  src/sellpilot/services/replenishment.py tests/unit/test_replenishment.py
uv run pytest tests/unit/test_replenishment.py -q

cd D:\SellPilot\frontend
npm.cmd run typecheck
npm.cmd run test:run -- tests/unit/commerce-workspaces.spec.ts
```
