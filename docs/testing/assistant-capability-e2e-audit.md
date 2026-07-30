# Assistant Capability E2E Audit

## 2026-07-30 运行稳定性复核

- 本轮开始 HEAD：`ff32e541e53b988e94e12cb9572f3eca417c9c9b`。
- 最新 `origin/develop`：`1dab0d2d9690790fa5729110e5864cac31880927`，包含 PR #50
  的商品描述数据质量与响应式详情修复。演示商品冲突按字段合并：保留 Assistant 新增的
  3 个新加坡母婴候选，并采用 develop 对既有 100 个商品的新版描述。
- Settings 唯一读取仓库根目录 `.env`。实际配置使用 `LLM_*` 作为 RAG 模型变量，
  使用 `DASHSCOPE_API_KEY`、`BAILIAN_*` 和 `CONTENT_MODEL_PROVIDER` 作为内容模型变量。
  敏感值未写入本文、日志或测试输出。
- 500 的可复现直接原因是：设置 `LLM_API_KEY` 后 RAG 进入 `LLMService`，
  运行时导入未声明也未安装的 `openai` 包并抛出 `ModuleNotFoundError`。现改为复用项目
  已使用的 `httpx` 调用 OpenAI-compatible 接口，并把 `httpx` 列为正式运行时依赖。
  401、403、404、429、5xx 和超时被保留为安全的模型调用失败摘要，不再成为未处理 500。
- 原后端 PID 早于 `.env` 修改时间，重启后新配置才生效。实际监听
  `127.0.0.1:8000`，Windows 排除端口范围为 `50000-50059`，因此 WinError 10013
  与本次 RAG 500 无关；重复启动由 `sellpilot-start-api` 的健康检查避免。
- 未处理异常现在记录带 Request ID 的完整 traceback；异常文本经过统一脱敏 formatter，
  API 响应仍只返回安全错误，不暴露堆栈。
- Content 英文表达 `content generation for product PROD-001 in English` 曾把普通单词
  `product` 误提取为商品 ID。产品 ID 正则现要求标识中至少包含一个数字，E2E 可正确解析
  `PROD-001` 并通过 Commerce normalization 读取稳定 ID `PROD0001`。
- PostgreSQL 验证：103 商品、263 SKU、263 库存、500 订单、451 物流、1000 评论、
  1 个知识文档/片段、100 个客服会话；`PROD0001` 关联 19 条评论。
- 真实业务 E2E：
  - 评论分析：19 条输入、16 条有效，情感分布正面 8 / 中性 1 / 负面 7；
  - 智能选品：新加坡母婴候选 3 个，Top 3 为 `PROD0102`、`PROD0101`、`PROD0103`；
  - Content：本地离线 Provider 通过统一 4 Step / 2 ToolCall 有界工作流；
  - RAG：退货政策命中 1 个来源，通过统一 Tool 与 Workflow；
  - 客服：普通商品分支、高风险人工分支均成功；Mock 模拟发送经 Confirmation，
    重复确认只产生 1 次成功写 ToolCall。
- 外部 Provider 验证只发送明确的合成连通性提示，不发送本地商品、知识库或会话载荷。
  Content 与 RAG 两套已配置端点均鉴权成功并返回结构化/非空结果。
- 本轮门禁：后端 Ruff 通过，Alembic 单一 head `20260728_0007` 且无待生成迁移，
  pytest 361 项通过；前端 30 个测试文件、
  144 项测试通过，构建成功，仅保留大 chunk 非阻塞警告。

审计日期：2026-07-29

开始审计 develop 基线：`abc9f7f70e7c77dc22a50a837da97734ecaba26b`

功能分支同步 merge commit：`a0ea780adcd02287cccc7b52550e4f4c18c01707`

最终同步 develop 基线：`49112310f6e7f888605dc0169ddb304518023347`
审计分支：`feature/assistant-workflow-integration`

## Git 与运行基线

- 开发前和推送前两次 develop 更新均通过无冲突 merge 同步到当前功能分支；最终同步
  包含 PR #49 的 AI 工作台状态恢复和产品改良草稿优化。
- 未进入 develop 的 `origin/feature/product-translation-workflow`
  （`9dbe99a`）未合并、未 cherry-pick。
- 唯一 Registry 运行实例包含 25 个 ToolDefinition、12 个
  WorkflowDefinition 和 10 个 Assistant Capability。
- Alembic 只有 `20260728_0007` 一个 head；`upgrade head` 成功，
  `alembic check` 无待生成迁移；本阶段无新增迁移。
- 本机 PostgreSQL 数据：103 商品、263 SKU、263 库存记录、500 订单、
  451 物流记录、1000 评论、100 客服会话、1 个 Mock 知识文档及 1 个知识片段。

## Capability 矩阵

| Capability | Service | ToolDefinition | ToolRegistry | WorkflowDefinition | WorkflowRegistry | Assistant API | 前端结果 | 测试/E2E | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `selection_analysis` | SelectionService / SelectionMarketRepository | `search_market_products`, `score_product_opportunity` | 是 | `selection`：查询、候选 Branch、评分、无数据终点 | 是 | plan/create/run | Top N、评分、完整度、来源；无数据提示 | Task `d56cf3b3…`：3 候选、2 ToolCall | available |
| `review_analysis` | ReviewAnalysisService / CommerceQueryService | `analyze_product_reviews` | 是 | `review_analysis` | 是 | plan/create/run | 评论数、情感、主题、痛点、代表证据 | Task `66984d0a…`：19 关联评论、16 有效评论 | available |
| `product_improvement` | ProductImprovementService + ReviewAnalysisService | `analyze_product_reviews`, `generate_product_improvement_plan` | 是 | `product_improvement`：已有分析或商品评论 Branch | 是 | plan/create/run | 结构化建议与证据 | Task `257f8a13…`：4 条建议 | available |
| `inventory_replenishment` | ReplenishmentService | `analyze_inventory_replenishment` | 是 | `inventory_replenishment` | 是 | plan/create/run | 补货建议，不自动改库存 | 既有全量回归 | available |
| `low_stock_check` | CommerceQueryService | `list_low_stock` | 是 | `low_stock_check` | 是 | plan/create/run | 低库存 SKU | 既有全量回归 | available |
| `order_query` | CommerceQueryService | `get_order`, `list_orders` | 是 | `order_query`：单笔/列表 Branch | 是 | plan/create/run | 订单列表或单笔结果 | 既有 Branch/审计测试 | available |
| `logistics_query` | CommerceQueryService | `get_order_logistics` | 是 | `logistics_query` | 是 | plan/create/run | 物流状态与节点 | 既有全量回归 | available |
| `content_generation` | ContentGenerationService / ModelGateway | `generate_localized_listing`, `check_listing_compliance` | 是 | `content_generation`：生成、事实/合规检查、有界质量记录 | 是 | plan/create/run | 标题、卖点、详情、FAQ、轮次 | Mock Provider Task `d864876c…`：1/3 轮通过 | available |
| `knowledge_query` | 复用 RAGService 和现有知识表 | `search_knowledge` | 是 | `knowledge_query` | 是 | plan/create/run | 有依据答案与来源；空命中拒答 | Task `c1c5b7d5…`：1 来源 | available |
| `customer_service_reply` | CustomerServiceService + 现有 Commerce/RAG/Adapter | 会话、分类、草稿、`mock_send_customer_reply` 等 | 是 | `customer_service_reply`：知识/订单/物流/商品/人工 Branch | 是 | plan/create/run | 草稿、依据、风险、人工处理、Mock 发送状态 | 普通、高风险、确认/幂等/恢复 E2E | available |

## 关键修复与真实证据

### Windows 启动

- 实际地址为 `127.0.0.1:8000`，PID `26536` 的 Python 进程已健康监听。
- IPv4/IPv6 excluded range 均为 `50000-50059`，8000 不在保留范围。
- 原启动脚本无条件再次启动 `uvicorn --reload`，重复绑定健康实例会触发
  WinError 10013；该错误与业务 Task 失败分离。
- `sellpilot-start-api` 现在读取 `API_HOST`/`API_PORT`，先检查健康接口；健康实例
  直接复用，未知端口占用明确报错且不 kill。根启动脚本把同一地址注入
  `VITE_PROXY_TARGET`。

### 评论与商品 ID

- 原失败 Task 的直接错误为 `RESOURCE_NOT_FOUND`，不是端口错误。
- 演示数据稳定 ID 是 `PROD0001`，用户常用输入为 `PROD-001`；统一
  Commerce normalization 现在只在 Service 层解析，Workflow 仍经
  TaskRunner → ToolExecutor。
- `PROD0001` 对应内部 UUID，实际关联 19 条评论；分析包含 16 条有效评论。
- 无评论时返回成功的 `no_data` 结果，不再抛出 500。
- Task 公共结果采用有界投影：保留指标和最多两条代表证据，不返回完整
  judgement、原始 serialized state 或内部堆栈。

### 选品

- 原“0 候选”来自 Workflow 只接受前端 candidate ID，以及中文类目未映射到稳定代码。
- `新加坡站` 标准化为 `sg`，婴儿/母婴表达集中映射到 `CAT008`。
- 新增 3 个明确标记为 `assistant_demo_mock` 的新加坡母婴候选。
- 查询顺序固定为市场商品 READ Tool → 数据完整度检查 → 确定性评分 → 排序。
- 缺少评论量或运营信号时不信任孤立评分，评分证据标记缺失并降低完整度。
- 真正无候选时返回 `no_data` 和中文调整条件提示，不包装成普通“分析 0 个成功”。

### Content、RAG、Customer Service

- Content 复用现有 ContentGenerationService 和 Provider 抽象；商品事实来自数据库。
  最多三轮，每轮记录生成摘要、事实/合规/SEO/本地化问题、是否重试及停止原因。
  默认只生成；现有保存草稿路径仍为 WRITE + Confirmation。
- 当前本机外部 `aliyun_bailian` Provider 曾出现一次
  `ModelGatewayError`（27.655 秒），失败 Task 保留且未伪造成功；Tool 现在稳定映射为
  `EXTERNAL_SERVICE_UNAVAILABLE`，前端显示中文可重试错误。项目明确的
  `offline_template` Mock Provider E2E 成功并标记 Provider/生成模式。
- RAG 复用现有 PostgreSQL 知识文档/片段与 RAGService；返回片段、来源、文档 ID、
  相关度、语言、更新时间和 Mock 标识；低于可靠阈值时拒答。
- 客服先读现有会话，再记录 Branch。退款、投诉、赔付、地址/订单修改、知识冲突、
  无可靠依据和低置信度进入人工处理。普通请求只生成草稿；显式“模拟发送”才选择
  HIGH_RISK Tool，进入 Confirmation。Task `6b84b321…` 重复确认只新增一条 Mock 消息，
  resume 后成功，且有 Step、ToolCall、Confirmation、OperationLog。

## 测试与演示数据

- `uv run ruff format --check .`：220 files already formatted。
- `uv run ruff check .`：All checks passed。
- `uv run pytest -q`：352 passed。
- `npm run format:check`：全部文件符合 Prettier。
- `npm run lint`：0 warning / 0 error。
- `npm run typecheck`：通过。
- `npm run test:run`：30 files、144 tests passed。测试退出码为 0；部分页面挂载时
  尝试访问未启动的本地 3000 端口并输出 `ECONNREFUSED` 诊断，不影响断言。
- `npm run build`：成功；仅保留 Vite 大 chunk 非阻塞警告。
- `sellpilot-import-mock-data` 重跑：校验 9254 行，0 插入、9255 跳过。
- `sellpilot-import-knowledge` 重跑：0 插入、1 跳过。

## 外部依赖与尚存风险

- 外部内容模型和 LLM 的可用性仍取决于本机配置与供应商状态；失败不会升级为成功，
  也不会暴露供应商响应或密钥。Mock 模式可使用明确标记的 offline Provider。
- 当前健康监听进程在本次代码修改前启动；启动器已证明会复用它，但要让该进程加载
  最新分支代码，需由操作者在合适时间正常重启，不能由自动化代理擅自终止。
- 前端全量测试的 localhost:3000 连接拒绝为既有组件的可观察诊断噪声，测试本身全部
  通过；没有把“后端已连接”硬编码为成功。
- 未合并的产品翻译 feature 分支必须先独立 PR 进入 develop，本轮没有直接接入。
