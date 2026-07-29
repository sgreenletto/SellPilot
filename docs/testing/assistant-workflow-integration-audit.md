# Assistant Workflow Integration 审计

## 审计基线

- 审计日期：2026-07-29（Asia/Shanghai）
- `develop` commit：`224590c2bbc2c48add4ba93ac40c9cb00f6f7fb7`
- `origin/develop`：`224590c2bbc2c48add4ba93ac40c9cb00f6f7fb7`
- 最新合并证据：
  - PR #44，`feature/dashboard-customer-service-tasks` → `develop`
  - merge commit：`224590c`
  - 标题：`feat: connect pending customer service sessions to dashboard`
  - 在它之前，PR #43（`c4398ab`）已合入知识翻译，PR #42（`b32f8b0`）已合入库存补货，PR #41（`18ac2bd`）已合入 Assistant Integration Foundation。
- 本地 `develop` 已通过 `git pull --ff-only origin develop` fast-forward 到该提交，功能分支从该提交创建。

## 远程未合并成员分支

`git branch -r --no-merged origin/develop` 仅发现：

- `origin/feature/product-translation-workflow`
- 未进入 `develop` 的提交：`9dbe99a fix: localize product category and status labels`
- 相对 `origin/develop` 的文件：
  - `docs/api/product-translation-contract.md`
  - `frontend/src/views/commerce/ProductsView.vue`
  - `frontend/tests/unit/commerce-workspaces.spec.ts`
- 规模：3 files changed，113 insertions，5 deletions。
- 该分支原 PR #24 已于 2026-07-28 合入 `develop`，但 `9dbe99a` 是 PR 合并后的新提交；GitHub API 未发现覆盖该新提交的开放 PR。
- 本轮未合并、未 cherry-pick、未复制该分支内容。

本机未安装 GitHub CLI，`gh pr list` 无法执行；PR #24、#44 状态使用 GitHub 只读 API 核验。

## develop 基线门禁

数据库迁移：

- `uv run alembic heads`：`20260728_0007 (head)`
- `uv run alembic current`：`20260728_0007 (head)`
- `uv run alembic check`：`No new upgrade operations detected.`
- 数据库已在 head，无需基线 upgrade，也没有理由创建新迁移。

后端：

- `uv run ruff format --check .`：失败，4 个文件不符合格式。
- `uv run ruff check .`：通过。
- `uv run pytest -q`：312 passed，3 failed。
- 三个失败均来自 PR #42 合入库存补货后没有同步稳定契约断言：
  - 工具目录缺少 `analyze_inventory_replenishment` 预期；
  - `TaskType` 预期缺少 `replenishment`；
  - 工具总数仍断言为 19。

前端：

- `npm run format:check`：失败，`dashboard.ts`、`ConversationView.vue` 等存在格式问题。
- `npm run lint`：失败，`ConversationView.vue` 有 2 个未使用导入。
- `npm run typecheck`：失败，`TrendDataset` 未导入、严格索引检查、未使用导入；PR #44 又把数值指标硬编码成字符串 `"已接入"`，增加类型失败。
- `npm run test:run`：在沙箱外可启动，106 passed，1 failed；Dashboard 测试 mock 覆盖了真实派生函数，成功路径被异常转为“后端未连接”。
- `npm run build`：通过；Vite 报告大 chunk 警告，但没有构建错误。

这些失败均可由确定的代码/测试集成遗漏解释，不依赖密钥，不需要 skip、删除或放宽测试。

## Capability 矩阵（`develop@224590c`）

状态严格使用 `available`、`contract_only`、`unavailable`、`duplicate`、`broken`。

| 能力 | Service | ToolDefinition | 是否注册 ToolRegistry | WorkflowDefinition | 是否注册 WorkflowRegistry | API | 前端页面 | 测试 | 实际状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `selection_analysis` | `SelectionService` | `score_product_opportunity` | 是 | `selection@1.0.0` | 是 | `/selection/*`、通用 `/tasks` | `SelectionWorkbenchView`、Assistant | Service/API/Tool/Workflow 测试 | `available` |
| `review_analysis` | `ReviewAnalysisService` | `analyze_product_reviews` | 是 | `review_analysis@1.0.0` | 是 | `/review-analysis/*`、通用 `/tasks` | `ReviewAnalysisView`、Assistant | Service/API/Tool/Workflow 测试 | `available` |
| `product_improvement` | `ProductImprovementService` | `generate_product_improvement_plan` | 是 | `product_improvement@1.0.0` | 是 | `/product-improvement/*`、通用 `/tasks` | `ProductImprovementView`、Assistant | Service/API/Tool/Workflow 测试 | `available` |
| `content_generation` | `ContentGenerationService` | `generate_localized_listing`、`check_listing_compliance` | 是 | 只有领域内 LangGraph 质量循环，没有统一 `WorkflowDefinition` | 否 | `/content-generation/*` | `ContentWorkshopView`、Assistant | Service/Tool/API/页面测试 | `contract_only` |
| `knowledge_query` | `RAGService`、`KnowledgeBaseService` | 无 | 否 | 无 | 否 | `/knowledge/retrieve`、`/knowledge/qa` | `KnowledgeBaseView`、Assistant | Knowledge API/页面测试 | `contract_only` |
| `customer_service_reply` | 无稳定专用 Service；页面直接组合 RAG 与 Commerce 查询 | 无 | 否 | 无 Branch/Risk/Handoff Workflow | 否 | 无稳定回复执行 API | `ConversationView`、Assistant | 仅页面/底层 API 覆盖 | `unavailable` |
| `inventory_replenishment` | `ReplenishmentService` | `analyze_inventory_replenishment` | 是 | `inventory_replenishment@1.0.0` | 是 | 通用 `/tasks`、`/tools` | `InventoryView` | 专用测试通过，但全局稳定契约断言失败 | `broken` |
| `low_stock_check` | `CommerceQueryService` | `list_low_stock` | 是 | 无 | 否 | `/commerce/inventory`、`/tools` | `InventoryView`、Assistant | Tool/API 测试 | `contract_only` |
| `order_query` | `CommerceQueryService` | `list_orders`、`get_order` | 是 | 无 | 否 | `/commerce/orders`、`/tools` | `OrdersView`、Assistant | Tool/API 测试 | `contract_only` |
| `logistics_query` | `CommerceQueryService` | `get_order_logistics` | 是 | 无 | 否 | `/commerce/orders/*/logistics`、`/tools` | `OrdersView`、Assistant | Tool/API 测试 | `contract_only` |

## 统一运行时与重复实现

- 唯一 `ToolRegistry`：`sellpilot.tools.registry.ToolRegistry`，由 `build_tool_registry` 构建并挂载到 `app.state`。
- 唯一 `ToolExecutor`：`sellpilot.tools.executor.ToolExecutor`。
- 唯一 `WorkflowRegistry`：`sellpilot.workflows.registry.WorkflowRegistry`，由 `build_workflow_registry` 构建并挂载到 `app.state`。
- 唯一 `TaskRunner`：`sellpilot.workflows.runner.TaskRunner`。
- 唯一持久化任务模型：`AgentTask` / `AgentTaskStep`；没有第二套 Task 表。
- 唯一工具调用、确认和操作日志模型：`ToolCall`、`ConfirmationTask`、`OperationLog`。
- `agents.registry.AgentRegistry` 是未注册业务 Agent 的未来工厂目录，不是第二套 Tool/Workflow/Task runtime。
- Content 的 LangGraph 是领域质量循环，不是第二个 `WorkflowRegistry`；但未适配统一 Task runtime，因此不能宣称 Assistant 可执行。

没有发现状态为 `duplicate` 的 Capability。

## 关键链路审计

1. 已注册 Workflow 的业务节点通过 `TaskRunner` 调用 `ToolExecutor`，没有直接从 Assistant API 调 Service/Repository/Adapter。
2. Content 具备事实、合规、SEO、本地化和完整性检查，并以 `max_attempts`（默认 3）限制质量循环；但尚未注册统一 Workflow。
3. RAG 复用了 `RAGService`，但 `/knowledge/qa` 直接构造并调用 Service，没有统一 Tool/Workflow 链。
4. Customer Service 没有基于政策、订单物流和高风险问题的稳定 Branch，也没有人工转交状态，必须保持 `unavailable`。
5. Inventory Replenishment 只生成确定性建议；工具风险为 READ，不调整库存。
6. Selection、Review、Improvement 均有稳定 Schema；Review 输出的 `analysis_id` 可作为 Product Improvement 输入。
7. Task、Step、ToolCall、Confirmation、OperationLog 通过 task/step/tool/confirmation ID 关联；公开查询按当前用户过滤。
8. Task API 不返回 `serialized_state`、内部 handler 或堆栈；Tool 元数据不返回 handler/module；公开载荷经过审计摘要和脱敏。
9. Task Center 已能展示 Task、Step、ToolCall、Confirmation、OperationLog，并读取 `task_id` 查询参数。
10. PR #44 没有接入其说明中的 Customer Service API，而是硬编码“已接入”；这是占位成功数据和类型错误，本功能分支恢复为明确“未接入”，并把评分/订单代理趋势标明为代理数据。

## 阻塞项与本阶段决策

满足进入实现的门槛：

- Assistant Integration Foundation 已通过 PR #41 进入 `develop`。
- 唯一 Registry / Executor / Runner 可用。
- Selection、Review、Product Improvement 至少一组能力可执行。
- Alembic 可升级且在 head。
- 全局失败有明确、可修复的集成原因。

本阶段允许接入：

- Selection、Review、Product Improvement。
- 修复全局契约后接入 Inventory Replenishment。
- 为现有 READ Tool 补齐统一 Workflow 后接入 Low Stock、Order Query、Logistics Query。

继续保持：

- Content Generation：`contract_only`，等待统一 WorkflowDefinition/Registry 接入。
- Knowledge Query：`contract_only`，等待 RAG Tool + Workflow 接入。
- Customer Service Reply：`unavailable`，等待明确 Branch、风险分类、政策/订单/物流组合和人工转交。

## 本功能分支修复后的状态

- `inventory_replenishment`：补齐 Assistant Capability 注册与全局契约测试后为 `available`。
- `low_stock_check`：新增 `low_stock_check@1.0.0` 后为 `available`。
- `order_query`：新增有界 Branch 的 `order_query@1.0.0`，实际分支写入 Step 输出后为 `available`。
- `logistics_query`：新增 `logistics_query@1.0.0` 后为 `available`。
- Content、Knowledge、Customer Service 状态未虚假升级。
- 没有新增数据库迁移。
