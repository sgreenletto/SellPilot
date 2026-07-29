# 智能选品 Service、API、Tool 与解释工作流

## 边界

本阶段把 `selection-v1.0.0` 确定性评分内核接入正式应用层。候选数据来自已导入数据库的 Mock Shopee 商品和最新类目趋势，不读取 CSV，也不依赖 `MockShopeeAdapter` 具体类。首版仍是单用户、单模拟店铺，不访问真实 Shopee。

分析任务只生成内部任务、计算结果和审计留痕，不修改商品、价格、库存或平台状态。导出接口返回既有结果的 JSON 表示及 SHA-256，不在服务端创建文件。因此这些能力按只读分析工具登记；任何后续平台写操作仍必须进入确认流程。

分析请求可选成本、物流成本和重量覆盖条件，并要求风险偏好。成本与物流覆盖值进入利润公式；
重量在当前没有运费阶梯的 Mock 数据中只作为透明任务条件保存；风险偏好选择版本化权重配置，
不得由前端自行计算或伪造评分。

## 调用链

```text
FastAPI selection endpoint
  -> SelectionService
    -> SelectionMarketRepository (Product + latest CategoryTrend)
    -> deterministic selection-v1.0.0 scorer
    -> validated explanation workflow
    -> SelectionRepository + internal TaskService
```

路由只处理认证、请求 Schema、响应封装和 request_id。候选筛选、站点映射、评分、解释校验、持久化、所有权校验、比较和导出均位于应用层。

## API

- `GET /api/v1/selection/candidates`：按站点、类目和价格筛选、排序及分页读取 Mock 候选。
- `POST /api/v1/selection/analyses`：创建内部选品任务并同步返回排序结果。
- `GET /api/v1/selection/analyses/{task_id}`：读取当前用户的任务和结果。
- `GET /api/v1/selection/analyses/{task_id}/compare`：比较同一任务内 2–10 个商品。
- `GET /api/v1/selection/analyses/{task_id}/export`：返回可下载 JSON 的元数据和内容。

全部接口要求 Bearer 认证。任务详情、比较和导出都校验 `created_by`，不存在或不属于当前用户时统一返回资源不存在。

## Tool

`register_selection_tools()` 将五个结构化工具注册到应用现有的生产
`ToolRegistry`：

- `search_market_products`
- `calculate_product_profit`
- `score_product_opportunity`
- `compare_products`
- `export_product_analysis_report`

工具输入和输出均由 Pydantic Schema 校验，并复用公共 `ToolRegistry` 的超时、脱敏摘要、耗时和 `ToolCall` 留痕。工具不会直接调用平台适配器或执行平台写操作。

生产环境不创建 Selection 专用 Registry。API、Workflow 或其他调用方如需按工具
语义调用这些能力，必须通过应用的 `ToolExecutor`；执行器在调用 handler 时注入当前
请求的受信数据库会话，handler 只将其交给 `SelectionService`。当前解释工作流本身是
Service 内部的有界 LangGraph，不调用 Tool handler，也不复制 ToolExecutor、
AgentTask 或 Confirmation 状态机。

## 解释可靠性

利润、利润率、归一化和总评分只由确定性内核计算。解释器只能接收评分结果中的事实；输出必须满足 `SelectionExplanation` Schema，并逐项匹配总分、利润、利润率和数据完整度。百炼模式调用真实模型生成简体中文解释；最多尝试两次，Schema 不合法、数值不匹配或模型调用失败时自动回退到明确标记的 `rule_template`。批量分析采用最多 4 路有界并发生成解释，避免逐商品串行调用造成页面超时；并发不会改变预先完成的确定性评分和排序。

物流风险由商品关联订单中的异常物流记录占比计算，售后风险由非驳回退货退款申请占商品
订单明细的比例计算；工厂适配由活跃 SKU 比例和达到安全库存的 SKU 比例等权计算。
确实没有关联业务数据时，评分内核仍会降低完整度并写入风险提示，不用零值冒充真实观测。
