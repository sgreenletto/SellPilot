# Assistant 发布后完成度审计

审计日期：2026-07-30

审计基线：`origin/develop@a6d9033997179b36d4a15a2f46108dbc5d901221`

稳定发布：`origin/main@12e3a121675e0731b38fb2b7fdd36b50ef5ffb35`、`v0.5.0`

本审计以源码、迁移、自动测试、本机 PostgreSQL 和实际 API 为证据，不以页面存在、
Registry 声明或旧交接文档作为完成依据。`COMPLETE` 表示当前 Mock Shopee 产品边界内
链路完整；不代表真实 Shopee 已接入。

| 模块/能力             | 页面           | API        | Service                   | Tool                            | Workflow                   | 数据                 | 自动测试        | 真实运行           | 当前状态             | 阻塞                       |
| --------------------- | -------------- | ---------- | ------------------------- | ------------------------------- | -------------------------- | -------------------- | --------------- | ------------------ | -------------------- | -------------------------- |
| 登录                  | 是             | 是         | 是                        | 不适用                          | 不适用                     | PostgreSQL 用户      | 是              | 已验证             | COMPLETE             | 无                         |
| Dashboard             | 是             | 是         | 是                        | 不适用                          | 不适用                     | Mock 商业数据        | 是              | 已验证             | COMPLETE             | 无                         |
| Assistant             | 聊天工作台     | plan/tasks | 是                        | 统一注册                        | 统一注册                   | Task 数据            | 是              | 已验证             | COMPLETE             | 无                         |
| Task Center           | 是             | 是         | 是                        | 不适用                          | 状态机                     | Task/Step            | 是              | 已验证             | COMPLETE             | 无                         |
| Confirmation          | 是             | 是         | 是                        | 风险门禁                        | 暂停/恢复                  | Confirmation         | 是              | 已验证             | COMPLETE             | 无                         |
| OperationLog          | Task Center    | 是         | Repository                | Tool 审计                       | Task 审计                  | OperationLog         | 是              | 已验证             | COMPLETE             | 无                         |
| Tool Runtime          | 元数据         | 是         | ToolExecutor              | 唯一 Registry                   | 不适用                     | ToolCall             | 是              | 已验证             | COMPLETE             | 无                         |
| Workflow Runtime      | 元数据         | 是         | TaskRunner                | 经 ToolExecutor                 | 唯一 Registry              | Step/State           | 是              | 已验证             | COMPLETE             | 无                         |
| MockShopeeAdapter     | Mock 标识      | status     | Adapter                   | 业务工具复用                    | 多工作流                   | 合成数据             | 是              | 已验证             | COMPLETE             | 无                         |
| RealShopeeAdapterStub | 无真实入口     | 失败边界   | Stub                      | 不可执行                        | 不可执行                   | 无                   | 是              | 非联网             | OUT_OF_SCOPE         | 真实平台未接入             |
| 市场数据              | 是             | 是         | SelectionMarketRepository | search_market_products          | selection                  | 103 商品快照         | 是              | 已验证             | COMPLETE             | 无                         |
| 智能选品              | 是             | 是         | SelectionService          | 查询/评分                       | selection Branch           | 3 个 SG 母婴候选     | 是              | 已验证             | COMPLETE             | 无                         |
| 评论分析              | 是             | 是         | ReviewAnalysisService     | analyze_product_reviews         | review_analysis            | 1000 评论            | 是              | 已验证             | COMPLETE             | 无                         |
| 产品改良              | 是             | 是         | ProductImprovementService | 分析/建议                       | product_improvement Branch | 评论证据             | 是              | 已验证             | COMPLETE             | 无                         |
| 商品管理              | 是             | 是         | CommerceQueryService      | 读写工具                        | 写入需确认                 | 103 商品             | 是              | 已验证             | COMPLETE             | 无                         |
| 内容生成              | 是             | 是         | ContentGenerationService  | 生成/合规                       | 有界 Loop                  | 商品事实/版本        | 是              | 已验证             | COMPLETE             | 外部模型可降为明确离线模式 |
| 商品草稿              | 是             | 是         | ContentGenerationService  | WRITE                           | Confirmation               | 内容版本             | 是              | 已验证             | COMPLETE             | 无                         |
| 模拟上下架            | 是             | 是         | CommerceOperationService  | HIGH_RISK                       | Confirmation               | Mock 状态            | 是              | 已验证             | COMPLETE             | 仅 Mock                    |
| SKU                   | 是             | 是         | CommerceQueryService      | 统一工具                        | 业务工作流复用             | 263 SKU              | 是              | 已验证             | COMPLETE             | 无                         |
| 库存                  | 是             | 是         | CommerceQueryService      | 库存工具                        | 查询工作流                 | 263 库存             | 是              | 已验证             | COMPLETE             | 无                         |
| 库存补货              | Assistant/库存 | 是         | ReplenishmentService      | analyze_inventory_replenishment | inventory_replenishment    | 真实 Mock 库存       | 是              | 已验证             | COMPLETE             | 只生成建议                 |
| 订单                  | 是             | 是         | CommerceQueryService      | get/list order                  | order_query Branch         | 500 订单             | 是              | 已验证             | COMPLETE             | 无                         |
| 物流                  | 是             | 是         | CommerceQueryService      | get_order_logistics             | logistics_query            | 451 物流             | 是              | 已验证             | COMPLETE             | 无                         |
| 客服                  | 是             | 是         | CustomerServiceService    | 会话/RAG/订单/发送              | Branch + Confirmation      | 100 会话             | 是              | 已验证             | COMPLETE             | RAG 政策分支受真实数据阻塞 |
| 知识库/RAG            | 是             | 是         | 唯一 RAGService           | search_knowledge                | knowledge_query            | 仅 1 个 Mock 文档    | 是              | Mock smoke 可用    | BLOCKED_RAG_DATA     | 待真实数据导入和命中验收   |
| PostgreSQL 初始化     | 不适用         | ready      | Alembic/CLI               | 不适用                          | 不适用                     | PostgreSQL 17        | 是              | 已验证             | COMPLETE             | 无                         |
| Mock 数据导入         | 不适用         | 不适用     | 幂等 Import Service       | 不适用                          | 不适用                     | 9 254 行来源包       | 是              | 已验证             | COMPLETE             | 无                         |
| 知识库导入            | 页面状态       | 是         | KnowledgeIngestionService | 不适用                          | 不适用                     | Mock 默认/真实待导入 | 是              | CLI 已备           | BLOCKED_RAG_DATA     | 待用户真实数据             |
| 管理员初始化          | 登录           | auth       | create-admin CLI          | 不适用                          | 不适用                     | 用户表               | 是              | 已验证             | COMPLETE             | 交互密码                   |
| 一键启动              | 浏览器入口     | health     | sellpilot-start-api       | 不适用                          | 不适用                     | 根 `.env`            | 是              | 已验证             | COMPLETE             | 无                         |
| 健康检查              | 连接状态       | live/ready | DB probe                  | 不适用                          | 不适用                     | PostgreSQL           | 是              | 已验证             | COMPLETE             | 无                         |
| Docker Compose        | frontend       | health     | 三容器                    | 不适用                          | migration before API       | volume               | 静态校验        | 未运行             | BLOCKED_LOCAL_DOCKER | 本机未安装 Docker          |
| GitHub Actions        | 不适用         | 不适用     | Postgres CI               | 不适用                          | 全门禁                     | 隔离 CI DB           | 配置已完成      | 待 PR 运行         | PARTIAL              | 需远程 CI 首次执行         |
| 安全配置              | 状态/错误      | 安全响应   | Settings/脱敏             | Tool 脱敏                       | 所有权/确认                | 根 `.env`            | 是              | 已审计             | COMPLETE             | 仍需常规依赖扫描           |
| README                | 不适用         | 不适用     | 不适用                    | 不适用                          | 不适用                     | 不适用               | 文档校验        | 已更新             | COMPLETE             | 无                         |
| 部署文档              | 不适用         | 不适用     | 不适用                    | 不适用                          | 不适用                     | 不适用               | 文档校验        | 命令审计           | COMPLETE             | Docker 实跑受阻            |
| 测试报告              | 不适用         | 不适用     | 不适用                    | 不适用                          | 不适用                     | 不适用               | 完整门禁        | 本轮更新           | COMPLETE             | 无                         |
| 演示脚本              | 不适用         | 真实 HTTP  | 不直连 Service            | 经 API                          | 经 API                     | PostgreSQL           | PowerShell 解析 | 待凭据实跑         | PARTIAL              | 需交互式管理员密码         |
| 新环境复现            | frontend       | backend    | init-demo                 | 不适用                          | 不适用                     | PostgreSQL           | 脚本/CI         | 本机既有环境已验证 | PARTIAL              | Docker 实跑和真实 RAG 数据 |

## 唯一运行时与跨模块边界

- 唯一 Tool Registry：`sellpilot.tools.registry.ToolRegistry`。
- 唯一 Workflow Registry：`sellpilot.workflows.registry.WorkflowRegistry`。
- 唯一 Task Runner：`sellpilot.workflows.runner.TaskRunner`。
- 所有 Workflow 业务工具经 `ToolExecutor`；写操作和 HIGH_RISK 操作进入既有
  `ConfirmationTask`，不会由页面直接写 Service。
- 选品、评论和产品改良可独立执行，产品改良已能从真实评论启动。首版没有把市场候选
  自动变成自有商品的跨域 composite workflow；这需要用户选择目标商品和业务授权，
  本阶段列为 `OUT_OF_SCOPE`，不伪造自动闭环。
- Content 的质量 Loop 最大三轮；客服 Branch 记录订单、物流、知识和人工路径。

## 当前发布结论

代码和 Mock Demo 主链路没有已知 P0 代码阻塞。真实 RAG 数据尚未导入，Docker 在本机
无法实跑，远程 CI 尚待功能分支 PR 触发。因此当前结论为 `NOT_RELEASE_READY`；完成
真实 RAG 命中、Docker/CI 外部验证后，可升级为候选发布状态。
