# SellPilot 成员三实施步骤计划

> **负责人**：成员三（李紫嫣）
>
> **负责范围**：智能选品、评论分析、产品改良、商品内容生成、Prompt 与模型管理、AI 评估，以及仓库外的软件著作权材料整理
>
> **目标里程碑**：以团队集成计划为准，建议对应 `v0.3.0` 业务能力里程碑
>
> **当前基线**：`v0.1.0 Foundation Milestone`，公共领域契约、成员三分析持久化基础及智能选品确定性计算内核已建立，成员三业务流程尚未实现
>
> **适用边界**：单用户、单模拟店铺、Mock Shopee；不接入或暗示已接入真实 Shopee
>
> **文档原则**：每一步形成可运行、可测试、可审查、可演示的增量，不以静态页面、硬编码结果或伪造 AI 调用代替真实实现

---

## 1. 文档目标

本文用于指导成员三按固定顺序完成全部负责内容，降低多人并行开发时的接口冲突、遗漏、返工和 Git 集成风险。

每一步必须同时满足：

1. 功能真实实现，不只完成页面外观或演示脚本。
2. 后端、前端、数据库、AI Schema、测试和文档保持一致。
3. 业务结论可解释、可追溯，选品结果不能由大模型直接拍分。
4. AI 输出使用明确的 Pydantic Schema，并在进入业务流程前校验。
5. 业务写操作先创建待确认任务，确认后才允许执行。
6. 上层业务只依赖统一接口，不直接读取 `MockShopeeAdapter` 具体实现。
7. 页面复用 `Sp*` 公共组件和 `--sp-*` 语义设计变量。
8. 每个任务在独立短期分支完成，通过 Pull Request 合入 `develop`。
9. 不提交密钥、`.env`、真实个人/店铺数据、缓存、构建产物或本地数据库。
10. 每步结束都有明确测试证据、已知问题和文档更新。

---

## 2. 当前状态与目标差距

### 2.1 当前已经具备

- FastAPI、统一响应、统一异常、认证和请求 ID。
- SQLAlchemy 2 异步会话及 Alembic 迁移机制。
- AgentTask、ConfirmationTask、ToolCall 和 OperationLog 公共底座。
- `PlatformAdapter` 抽象、`MockShopeeAdapter` 占位实现和 `RealShopeeAdapterStub`。
- 结构化 `ToolRegistry`、风险阻断、超时和调用记录。
- LangGraph 公共 State、工作流注册器和 diagnostic 工作流。
- Vue 3、TypeScript、Vite、Pinia、Vue Router。
- `Sp*` 公共组件、设计变量、统一 HTTP 客户端和错误模型。
- `/market/selection`、`/market/reviews`、`/products/content` 占位路由。
- `data/demo/shopee_mock/` 已合入成员二生成并校验通过的完整模拟实验数据。
- 公共领域枚举、Schema、API 包络、分页、状态流转、`RiskLevel` 与 `ToolRiskLevel` 分离契约。
- 分析与内容持久化模型、Repository、Alembic `20260727_0002` 迁移及隔离测试。
- 不依赖 LLM 的智能选品利润、归一化、可解释评分、缺失数据证据和稳定排序内核。

### 2.2 当前尚未具备

- 评论语言处理、情感/主题/痛点分析及证据引用。
- 产品改良建议和报告生成。
- 商品多语言内容生成、事实校验、合规校验及版本管理。
- 成员三的正式 Service、Repository、API、Tool、Workflow。
- 三个业务页面及商品对比、详情、报告、版本对比界面。
- Prompt 版本、模型调用统计和 AI 评估体系。
- 成员三端到端测试、说明文档、报告样例，以及仓库外单独管理的软著材料。

不得在上述功能完成前将其描述为“已实现”或“可生产使用”。

---

## 3. 强制架构边界

### 3.1 后端调用方向

```text
FastAPI endpoint
  → application service
  → domain calculation / workflow
  → repository / report service / model gateway / PlatformAdapter
  → SQLAlchemy / ToolRegistry / LangGraph / external model
```

- endpoint 只负责协议转换、参数校验、鉴权和调用 Service。
- 确定性算法放在独立 domain/service 模块，不放在路由或 Vue 页面中。
- Repository 负责数据访问，不混入评分、Prompt 或页面展示逻辑。
- 模型调用通过统一 Model Gateway，不允许各 Service 自行读取 API Key 或拼装客户端。
- 平台数据通过统一 Repository/Service/`PlatformAdapter` 获取，不直接依赖 CSV 路径。

### 3.2 前端调用方向

```text
View
  → 业务组件 / Sp 公共组件
  → composable / Pinia
  → src/api/*
  → FastAPI /api/v1
```

- View 不直接调用 `fetch`。
- View 不创建 ECharts 实例。
- 导航只在 `config/navigation.ts` 维护。
- 大型 Mock 数据不写入 View。
- 后端不可达时显示“后端未连接”，不得用本地成功结果掩盖错误。

### 3.3 AI 与写操作边界

- LLM 只负责语言理解、解释、分类建议和内容生成，不负责金额、利润或最终评分计算。
- LLM 输出必须经过结构化 Schema 校验、业务规则校验和错误处理。
- 所有重试必须设置最大次数和超时，禁止无限循环。
- 生成分析但不修改业务数据的工具标记为只读。
- 创建商品草稿、保存内容版本、采纳改良建议等持久化业务操作必须进入待确认流程。
- AgentTask、ConfirmationTask 只能由内部 Service 创建，不新增公共创建 API。
- 系统任务、日志等内部记录是否属于免确认基础设施写入，必须在对应功能开发前依据最新 `develop` 的公共服务实现核对；无法从代码和现有架构文档确认时，只向成员一确认该冲突点，不自行假设。

---

## 4. 成员二模拟数据使用规则

模拟数据当前已进入仓库 `data/demo/shopee_mock/`。该目录是数据资产和初始化输入，不是成员三业务层应直接依赖的运行时接口。

### 4.1 主要输入

| 文件 | 用途 |
| --- | --- |
| `data/demo/shopee_mock/products.csv` | 商品、站点、类目、价格、成本、物流成本、销量、评分、评论量、收藏量 |
| `data/demo/shopee_mock/skus.csv` | SKU 价格、成本、重量和规格 |
| `data/demo/shopee_mock/reviews.csv` | 多语言评论、中文内容、评分、情感提示、问题类型 |
| `data/demo/shopee_mock/category_trends.csv` | 搜索指数、销售指数、竞争指数、平均价格和增长率 |
| `data/demo/shopee_mock/orders.csv` / `data/demo/shopee_mock/order_items.csv` | 销售和订单侧辅助校验 |
| `data/demo/shopee_mock/returns_refunds.csv` | 售后风险辅助指标 |

### 4.2 使用限制

- 全部数据均为模拟实验数据，页面、接口和报告必须保留来源与 Mock 标识。
- 不同站点币种不能直接相加或直接按金额横向比较。
- 数据进入分析层前必须通过成员二的数据实体、Repository 或 API。
- 不得在成员三业务代码中硬编码 ZIP 路径、CSV 列名或本地微信目录。
- 不得将 `sentiment_hint`、`issue_type` 宣称为真实人工标注结论；它们可作为模拟基准和测试标签。
- 当前没有真实工厂能力数据。“工厂适配度”必须使用书面确认的代理指标，或者明确显示“数据不足”，不能伪造。

---

## 5. 总体实施顺序

| Step | 阶段 | 可验收成果 | 建议短期分支 |
| ---: | --- | --- | --- |
| 0 | 计划与基线确认 | 计划评审通过，范围无歧义 | `docs/member3-implementation-plan` |
| 1 | 数据模型与迁移 | 成员三表结构可 upgrade/downgrade | `feature/analysis-persistence` |
| 2 | 选品计算内核 | 利润、指标、归一化和评分可独立测试 | `feature/selection-scoring` |
| 3 | 选品服务、API 与工具 | 真实接口返回可解释选品结果 | `feature/selection-api-tools` |
| 4 | 智能选品前端 | 条件配置、结果排序、详情和对比可用 | `feature/selection-pages` |
| 5 | 评论分析内核 | 多语言、情感、主题、痛点和证据结构可用 | `feature/review-analysis` |
| 6 | 评论服务、API 与工具 | 评论分析任务可通过正式接口运行 | `feature/review-api-tools` |
| 7 | 评论分析前端 | 评论、趋势、痛点和证据页面可用 | `feature/review-pages` |
| 8 | 产品改良与报告 | 建议、优先级、置信度和报告可追溯 | `feature/improvement-reports` |
| 9 | 产品改良前端 | 建议编辑、采纳流程和报告展示可用 | `feature/improvement-pages` |
| 10 | Prompt、模型网关与观测 | Prompt 版本和模型调用记录可追踪 | `feature/ai-model-management` |
| 11 | 内容生成与质量循环 | 多语言内容经过事实和合规检查 | `feature/content-generation` |
| 12 | 内容 API、工具与版本 | 内容版本、对比和草稿确认流程可用 | `feature/content-api-tools` |
| 13 | 内容工坊前端 | 生成、编辑、校验、对比和恢复可用 | `feature/content-workshop` |
| 14 | AI 评估体系 | 固定测试集、指标、失败样例和报告 | `feature/ai-evaluation` |
| 15 | 全链路联调与加固 | 两条成员三核心闭环端到端通过 | `feature/member3-integration` |
| 16 | 文档与交付 | 仓库技术文档完整，仓库外软著材料另行整理 | `docs/member3-delivery` |

> 分支名称必须在创建前由本人再次运行 `git branch --list` 和 `git branch -r` 检查，避免与团队已存在分支冲突。
>
> 表中分支只是建议名；如果组长已为任务指定名称，以组长要求为准。

### 5.1 临时分支数量

按当前计划严格执行时，共建立 **17 个短期分支**：

- Step 0 当前计划文档：1 个 `docs/*` 分支。
- Step 1—16 后续实施：16 个短期分支。
- 类型分布：2 个 `docs/*` 分支和 15 个 `feature/*` 分支。

当前文档合入后，成员三还需要依次完成 **16 个后续短期分支**。这些分支不是同时建立，也不长期保留；默认任意时刻只维护一个当前任务分支。

每个 Step 对应一个短期分支。除非团队评审明确决定合并两个高度耦合、无法独立验收的 Step，否则不得为了减少分支数量而把算法、API、页面、测试和无关修复全部塞进一个长期大分支。

### 5.2 每个分支何时合入 `develop`

每个产生仓库变更的 Step 完成后立即独立合入 `develop`，不等成员三所有功能全部做完再一次性合并：

```text
最新 develop
→ 创建当前 Step 短期分支
→ 完成功能、测试和文档
→ 在当前分支同步 origin/develop
→ 解决冲突并重新执行检查
→ 创建 PR（base: develop）
→ 评审通过后合入 develop
→ 删除当前短期分支
→ 拉取最新 develop
→ 再创建下一个 Step 分支
```

合并门槛如下：

1. 本 Step 的功能和异常路径真实完成。
2. 本 Step 的 MVP 验收通过。
3. 相关格式、静态检查、测试和构建通过。
4. 需求、架构、API 或测试文档已按影响同步。
5. `git diff --check` 通过，暂存区和提交中没有无关文件。
6. PR 已说明改动、未改动、测试、风险和对其他模块的影响。
7. 评审意见处理完成。

禁止从尚未合入的上一个 Step 分支继续创建下一个分支，否则会形成层叠分支，导致 PR 混入前一任务的提交。确需并行时，必须由团队明确安排，并保证两个分支都从最新 `develop` 创建、文件边界互不冲突。

### 5.3 `main` 与 Tag 时机

- 所有产生仓库变更的短期分支都只通过 PR 合入 `develop`，不直接合入 `main`。
- 成员三 Step 16 完成，只代表成员三范围完成，不自动触发 `main` 合并或 Tag。
- 需要等待团队选定的完整里程碑范围全部进入 `develop`，再执行前后端全量测试、迁移验证、演示验收和文档核对。
- 只有上述检查通过后，才由团队按发布流程将 `develop` 合入 `main`。
- Tag 只在 `main` 的稳定里程碑提交上创建；开发中的每个 Step、功能分支和 `develop` 都不打 Tag。
- 目前不需要为本实施计划或中间 Step 处理 Tag。
- 当前有效的 `docs/git-workflow.md` 明确规定 Tag 只能由组长创建。如果团队以后变更执行人，必须先通过 PR 更新该书面规则，再按新规则操作；在此之前成员三不创建 Tag。

---

## 6. 分步骤实施细则

## Step 0：计划评审与开发基线确认

| 项目 | 内容 |
| --- | --- |
| 目标 | 让成员一、二、三、四对成员三范围、输入、输出和依赖达成一致 |
| 输入 | 总需求、成员分工、前端负责人表、Git 规则、模拟数据说明 |
| 输出 | 本计划评审意见和需要调整的事项 |
| MVP | 团队可以明确回答“成员三做什么、依赖谁、向谁提供什么” |

### 必做事项

- [ ] 确认当前开发基线确为最新 `develop`。
- [ ] 确认成员三对应负责人表中的李紫嫣。
- [ ] 确认 Prompt 配置页属于 P1，不阻塞 P0 主闭环。
- [ ] 确认 AI 评估页面是否必须做页面；即使暂缓页面，测试集和评估报告也必须完成。
- [ ] 确认 `v0.3.0` 是否作为成员三能力里程碑；Tag 按当前 `docs/git-workflow.md` 由组长在稳定 `main` 上创建。
- [ ] 将需要保留的评审结论更新到本文对应位置。

### 验收

- 文档中的职责与团队口头约定一致。
- 没有把成员二的数据后台或成员一的 Agent 总编排划入成员三。
- 没有遗漏软件著作权材料责任，并明确软著申请材料不进入代码仓库。

### 建议提交

```text
docs: add member three implementation plan
```

---

### 已冻结的跨成员公共契约与后续确认点

| 项目 | 内容 |
| --- | --- |
| 目标 | 在编码前冻结成员三依赖的业务实体、API、错误和确认流程 |
| 依赖 | 成员一公共架构、成员二数据实体和导入方案 |
| 输出 | 数据字典映射、接口契约、Schema 草案、错误码、状态和责任矩阵 |
| MVP | 使用合成对象即可完成选品、评论和内容接口的契约测试 |

### 与成员二确认

- 商品、SKU、评论、趋势、订单和售后实体的字段、类型、主外键。
- 站点、语言、币种、类目、来源类型和 Mock 标识枚举。
- 列表分页、筛选、排序及数据更新时间。
- 评论和趋势数据的 Repository/Service/API 入口。
- 选品分析层需要的数据是否一次聚合返回，避免 N+1 查询。
- 数据不足、缺失值、异常值和未支持站点的返回方式。

### 与成员一确认

- 成员三新表的命名和公共字段。
- Tool 命名、`ToolRiskLevel`、超时、输入/输出 Schema 和注册方式；业务风险单独使用 `RiskLevel`。
- Workflow 注册名、AgentTask 类型和节点结果格式。
- 只读分析、保存报告、创建草稿、保存内容版本分别如何进入确认流程。
- 报告文件存储和导出接口。
- 模型配置、密钥读取、Token 统计和日志脱敏的公共实现位置。

### 与成员四确认

- 选品、评论、改良和内容页面所需 API。
- 公共页面组件是否已有或需要扩展。
- 客服反馈如何向产品改良模块提供结构化输入。
- 商品改良草稿如何跳转到商品管理或内容工坊。

### 必须形成的 Schema 草案

- `SelectionCriteria`
- `SelectionMetricBreakdown`
- `ProductSelectionResult`
- `ReviewAnalysisRequest`
- `ReviewEvidence`
- `ReviewAnalysisResult`
- `ImprovementSuggestion`
- `ProductImprovementReport`
- `ListingGenerationRequest`
- `LocalizedListingContent`
- `ListingComplianceResult`
- `ContentVersionSummary`
- `ModelInvocationSummary`

### 验收

- OpenAPI 示例与前端类型可以一一对应。
- 金额使用精确十进制类型，时间带时区。
- 任何结论结构都包含来源或证据字段。
- 所有写操作的确认方式已明确。
- 后续业务 Schema、页面和算法实现不得绕开已冻结的公共契约。

公共契约以 `docs/architecture/domain-contracts.md` 和 `docs/api/common-contracts.md` 为准；成员三业务 Schema 在对应功能 Step 内实现，不在公共模块中重复定义。

---

## Step 1：成员三数据模型、Repository 与 Alembic 迁移

> **状态**：分析与内容持久化基础已完成，包括模型、Repository、Alembic `20260727_0002` 迁移和隔离测试；本 Step 不代表选品、评论分析、产品改良或内容生成算法已经实现。

| 项目 | 内容 |
| --- | --- |
| 目标 | 建立可追踪、可版本化、可回滚的分析与内容持久化基础 |
| 依赖 | 最新 `develop` 的公共架构、成员二数据实体和导入结果 |
| MVP | `alembic upgrade head → downgrade → upgrade` 完整通过 |

### 已建立数据对象

当前持久化基础已经覆盖：

- 选品任务与结果。
- 评论分析结果及证据关联。
- 产品改良报告及建议项。
- 商品内容及内容版本。
- Prompt 模板及 Prompt 版本。
- 模型调用记录或与公共 ToolCall/AgentTask 的关联。
- 生成报告记录。

### 已落实的实现要求

- 只通过 Alembic 维护正式结构，不在应用启动时 `create_all`。
- UUID、时间、JSON/JSONB、索引和命名规则与公共模型一致。
- 结果表保存算法/Prompt/模型版本，保证结果可复现。
- 报告和证据引用保存稳定 ID，不保存无法追踪的纯文本快照。
- Repository 只负责查询和持久化。
- 补充 SQLite 隔离测试和 PostgreSQL 兼容性说明。

### 已覆盖测试

- 迁移 upgrade/downgrade/upgrade。
- 主键、外键、唯一约束和必要索引。
- Repository 创建、查询、分页和状态过滤。
- 删除或归档策略不破坏证据链。

### 已完成验收

- 新环境可仅靠 Alembic 建立表结构。
- 没有本地数据库或生成 SQL 被提交。
- 模型和迁移文档同步更新。

### 实现记录

```text
feat: add analysis persistence models
feat: add analysis database migration
test: cover analysis repositories and migration
docs: document analysis data model
```

---

## Step 2：智能选品确定性计算内核

| 项目 | 内容 |
| --- | --- |
| 目标 | 建立不依赖 LLM、可解释、可复现的选品评分算法 |
| 依赖 | 成员二统一数据实体和可用指标输入 |
| MVP | 给定固定候选数据，稳定输出分项分数、总分、排名和依据 |

### 计算模块

1. 数据完整性检查。
2. 售价、成本、物流成本和利润计算。
3. 利润率及最低利润过滤。
4. 搜索/销售热度及增长率。
5. 竞争程度。
6. 评论质量。
7. 物流风险。
8. 售后风险。
9. 工厂适配代理指标或数据不足标记。
10. 指标归一化。
11. 权重校验和总分计算。
12. 并列排序和稳定排序。
13. 数据完整度和置信度。
14. 基于真实指标的规则化推荐事实。

### 算法约束

- 金额和利润使用 `Decimal`，不使用二进制浮点做最终金额判断。
- 不同站点分别归一化，除非明确完成汇率换算。
- 权重和公式进入版本化配置，不散落魔法数字。
- 缺失值处理必须明确，不能静默当作 0。
- 极值、全相等、单候选、负利润和空数据都有定义。
- LLM 不得修改分数，只能把已计算指标转成自然语言解释。

### 单元测试

- 正常利润、零利润、负利润。
- 最低利润过滤边界。
- 单候选、全相等、极端离群值。
- 权重和不等于 1、负权重、未知指标。
- 缺失趋势、缺少评论、缺少售后数据。
- 跨币种隔离。
- 排名稳定性和可复现性。
- 固定数据集黄金结果。

### 验收

- 不调用 LLM 即可完成全部评分。
- 每个分数都能追溯到输入字段和公式版本。
- 重复输入得到相同输出。
- 算法测试覆盖关键边界，而不只覆盖正常示例。

### 建议提交拆分

```text
feat: implement product profit calculation
feat: implement explainable selection scoring
test: cover selection scoring edge cases
docs: document selection metrics and formulas
```

---

## Step 3：智能选品 Service、API、Tool 与工作流

| 项目 | 内容 |
| --- | --- |
| 目标 | 将选品内核接入正式分层、ToolRegistry 和工作流 |
| 依赖 | Step 1、Step 2、成员二市场数据查询 |
| MVP | 认证用户通过 API 提交条件并获得结构化、可解释结果 |

### 后端实现

- `SelectionService`：用例编排、权限、数据检查和结果聚合。
- Repository：任务、结果和报告查询。
- API：条件校验、候选查询、分析、详情、对比和导出入口。
- Tool：
  - `search_market_products`
  - `calculate_product_profit`
  - `score_product_opportunity`
  - `compare_products`
  - `export_product_analysis_report`
- Workflow：读取候选 → 完整性检查 → 计算 → 排序 → 解释 → 解释核验。

### AI 解释要求

- 输入只包含已计算指标和必要商品事实。
- 输出引用指标名、数值、数据来源和风险。
- Schema 校验失败时有限重试。
- 解释与指标不一致时返回明确错误或规则化降级解释。
- 降级结果必须标注为规则模板生成，不伪装成模型结果。

### API 测试

- 正常条件、无候选、非法区间、未知站点。
- 分页、筛选和排序。
- 未登录访问。
- Tool 输入/输出 Schema。
- Tool 超时和失败。
- 模型解释失败与降级。
- 报告导出元数据。

### 验收

- 路由中无评分业务逻辑。
- ToolRegistry 能记录调用摘要和耗时。
- 返回统一 API 结构和 request ID。
- 结果明确显示 Mock 来源。
- Swagger/OpenAPI 示例可直接用于前端联调。

### 建议提交拆分

```text
feat: add selection application service
feat: expose selection api and tools
feat: add selection explanation workflow
test: cover selection api and tools
docs: document selection api
```

---

## Step 4：智能选品、详情与商品对比前端

| 项目 | 内容 |
| --- | --- |
| 目标 | 完成负责人表第 31—36 项 |
| 依赖 | Step 3 API 稳定；公共组件可用 |
| MVP | 用户配置条件后能看到真实后端结果、排序、详情、对比和报告入口 |

### 页面功能

- 站点、类目、价格、成本、物流、最低利润、重量和风险偏好。
- 候选商品选择和条件校验。
- 需求、竞争、利润、评论、物流和售后分项评分。
- 总分、排名、数据完整度和数据来源。
- AI 推荐解释和风险提示。
- 商品详情抽屉或独立详情。
- 2—4 个候选商品对比。
- 导出和报告生成状态。
- 加载、空数据、错误、超时和后端未连接状态。

### 前端约束

- View 不直接 `fetch`。
- 新增 `src/api/selection.ts` 和严格 TypeScript 类型。
- ECharts 仅在图表组件内初始化、resize 和 dispose。
- 复用 `SpButton`、`SpCard`、`SpInput`、`SpSelect`、状态组件和设计变量。
- 状态不仅依靠颜色。
- 响应式覆盖 `<768px`、`<1024px` 和桌面宽度。
- URL 或 Pinia 状态是否保存筛选条件，需在开发前确定。

### 前端测试

- 表单边界与禁用状态。
- 成功、无结果、错误和超时。
- 排序和对比选择。
- API 参数转换。
- 后端未连接提示。
- 键盘操作、focus-visible 和基础可访问性。
- 移动端布局关键节点。

### 验收

- 页面展示来自正式 API，不读取静态结果数组。
- 所有负责人表功能均能实际操作。
- 运行 `format:check`、`lint`、`typecheck`、`test:run` 和 `build`。
- 完成后提醒本人在《跨境电商AI平台前端页面负责人安排.xlsx》第 31—36 项“完成情况”填写“李紫嫣”。

### 建议提交拆分

```text
feat: add selection api client and types
feat: implement product selection pages
feat: add product comparison components
test: cover product selection views
docs: document selection page usage
```

---

## Step 5：评论分析内核

> **实现状态**：已在 `feature/review-analysis-core` 完成领域内核与离线测试，待审核合并；Service、API、Tool、Workflow 和页面仍按 Step 6—Step 7 实施。

| 项目 | 内容 |
| --- | --- |
| 目标 | 建立多语言、证据驱动、可评估的评论分析流水线 |
| 依赖 | 成员二评论查询和公共 Schema 边界 |
| MVP | 对固定评论集合输出情感、主题、痛点、趋势和代表证据 |

### 分析流程

```text
读取评论
→ 数据质量检查
→ 语言检测/校验
→ 翻译或统一分析语言
→ 情感分析
→ 主题分类
→ 痛点聚类
→ 代表评论提取
→ 统计聚合
→ 站点/时间趋势
→ Schema 与证据校验
```

### 分类要求

- 产品质量。
- 包装。
- 文案或描述不符。
- 物流。
- 服务。
- 材料。
- 尺寸/规格。
- 错发/漏发。
- 其他和无明确问题。

### 证据要求

- 每个主题和痛点至少关联稳定 `review_id`。
- 保存原文、展示翻译、语言和评分。
- 区分统计事实、模型判断和人工修改。
- 代表评论必须来自输入集合，禁止模型编造。
- 翻译失败时保留原文并标记状态。

### 测试

- 六种语言及未知语言。
- 空评论、重复评论、纯表情、垃圾文本和超长文本。
- 正/中/负评论。
- 多主题评论。
- 证据 ID 不存在时校验失败。
- 模型返回非法 JSON、未知主题、空证据和超时。
- 趋势聚合和站点隔离。

### 验收

- 所有聚合数字可由输入评论重新计算。
- 模型只输出允许的主题和证据 ID。
- 失败不会生成看似成功的空报告。
- 可用 Fake Model 完成离线自动化测试。

### 建议提交拆分

```text
feat: implement multilingual review preprocessing
feat: implement evidence based review analysis
test: cover review analysis edge cases
docs: document review taxonomy and evidence rules
```

---

## Step 6：评论分析 Service、API、Tool 与工作流

> **实现状态**：已在 `feature/review-analysis-service` 完成应用层、分阶段 API、Tool、AgentTaskStep 工作流、幂等和批处理，待审核合并；评论分析前端仍按 Step 7 实施。

| 项目 | 内容 |
| --- | --- |
| 目标 | 将评论流水线接入持久化、API、工具和 Agent 任务 |
| 依赖 | Step 1、Step 5 |
| MVP | 可按商品、站点和时间范围运行并查询分析任务 |

### 实现内容

- `ReviewAnalysisService`。
- 分析任务创建、进度、失败原因和结果查询。
- 评论列表、筛选、分页和证据详情。
- Tool：
  - `get_product_reviews`
  - `analyze_product_reviews`
- 工作流节点状态写入 AgentTaskStep。
- 幂等键或重复任务策略。
- 大批量评论的分页/批处理策略。

### 测试

- 正常任务、空数据、重复提交。
- 节点失败和最大重试。
- 任务状态及错误保存。
- Schema 校验失败。
- 未登录和资源不存在。
- 敏感字段不进入日志。

### 验收

- 长任务能显示状态，而不是请求一直无反馈。
- Tool 调用有输入/输出摘要、耗时和错误。
- 结果包含算法/Prompt/模型版本。
- API 文档同步更新。

### 建议提交拆分

```text
feat: add review analysis service and workflow
feat: expose review analysis api and tools
test: cover review analysis tasks
docs: document review analysis api
```

---

## Step 7：评论分析前端

> **实现状态**：已在 `feature/review-analysis-workbench` 完成评论筛选、分析概览、
> 趋势、证据分页与定位、任务错误状态及 Step 8 入口，待审核合并。

| 项目 | 内容 |
| --- | --- |
| 目标 | 完成负责人表第 37—40 项，并为第 41—43 项提供入口 |
| 依赖 | Step 6 |
| MVP | 可选择商品并查看评论、翻译、情感、主题、痛点、趋势和证据 |

### 页面功能

- 商品、站点、评分、语言、情感、主题和时间筛选。
- 评论原文与翻译。
- 情感分布。
- 高频主题和痛点。
- 产品、包装、文案、物流、服务问题分类。
- 时间趋势和站点差异。
- 代表评论及证据引用。
- 任务进度、失败原因和重新运行。
- 跳转产品改良报告。

### 测试与验收

- 筛选、分页和详情。
- 证据点击定位对应评论。
- 空数据、失败、超时和后端未连接。
- 图表组件生命周期。
- 响应式和键盘操作。
- 完成后先提醒本人核对负责人表第 37—40 项；第 41—43 项必须等 Step 9 真正完成后再填写名字。

### 建议提交拆分

```text
feat: add review analysis api client
feat: implement review analysis page
feat: add review evidence and trend components
test: cover review analysis view
```

---

## Step 8：产品改良建议与报告服务

| 项目 | 内容 |
| --- | --- |
| 目标 | 将评论证据转成面向运营和工厂的结构化改良方案 |
| 依赖 | Step 6 评论分析结果 |
| MVP | 生成带频率、严重度、优先级、置信度和证据的改良报告 |

### 建议结构

- 问题类型和问题描述。
- 发生频率及样本量。
- 严重度。
- 影响站点和 SKU。
- 建议措施。
- 产品结构、材料、规格、包装或体验方向。
- 实施优先级和理由。
- 置信度。
- 支撑评论 ID。
- 数据限制和不确定性。

### 规则

- 频率由统计计算，不由 LLM 编造。
- 优先级至少考虑频率、严重度和业务影响。
- 置信度必须与样本量、数据完整度和模型判断关联。
- 工厂建议不能超出已知商品事实；信息不足时明确说明。
- 每条建议必须有证据或明确标记为低置信度推断。

### 报告与工具

- `generate_product_improvement_plan`
- `export_product_analysis_report`
- 报告保存输入条件、数据来源、模型/Prompt/算法版本和生成时间。
- 导出格式以团队报告服务能力为准，至少保证一种稳定格式。

### 测试

- 无痛点、单一痛点、冲突痛点和少样本。
- 证据完整性。
- 优先级排序。
- 模型幻觉和事实冲突拦截。
- 报告生成失败。

### 验收

- 报告数字与评论统计一致。
- 所有建议可定位证据。
- 导出文件不含密钥、真实个人信息或本地绝对路径。

### 建议提交拆分

```text
feat: implement product improvement planning
feat: add evidence based improvement reports
test: cover improvement prioritization and reports
docs: add product improvement report specification
```

---

## Step 9：产品改良报告前端与草稿确认入口

| 项目 | 内容 |
| --- | --- |
| 目标 | 完成负责人表第 41—43 项 |
| 依赖 | Step 8、成员一确认服务、成员二商品草稿服务 |
| MVP | 用户可查看、编辑、采纳/忽略建议，导出报告并发起草稿待确认任务 |

### 页面功能

- 建议列表、优先级、置信度和证据。
- 建议详情及评论定位。
- 人工编辑、采纳和忽略。
- 工厂报告预览和导出。
- “创建改良商品内容草稿”只创建待确认任务。
- 待确认、已确认、已取消、执行失败状态。
- 跳转任务中心查看执行结果。

### 确认流程

```text
用户选择建议
→ 预览修改内容
→ 内部 Service 创建 ConfirmationTask
→ 前端跳转/展示待确认
→ 用户确认
→ 执行器创建草稿
→ 保存操作结果和日志
```

### 验收

- 点击创建草稿时不会绕过确认直接写业务数据。
- 重复确认不会重复创建草稿。
- 修改前后内容和风险提示清晰。
- 完成后提醒本人在负责人表第 41—43 项填写“李紫嫣”。

### 建议提交拆分

```text
feat: implement product improvement report page
feat: add confirmed improvement draft flow
test: cover improvement confirmation states
```

---

## Step 10：Prompt、模型网关与调用观测

| 项目 | 内容 |
| --- | --- |
| 目标 | 统一模型调用，保证 Prompt 可版本化、调用可测试、成本可追踪 |
| 依赖 | 成员一配置和日志约定 |
| MVP | 选品解释、评论分析和内容生成通过同一模型接口调用 |

### 实现内容

- Model Gateway 抽象。
- 真实模型实现、Fake Model 测试实现和明确标识的离线演示降级。
- Prompt 模板、任务类型、语言、版本、状态和变更说明。
- 模型名、参数、超时、重试、Token、耗时和错误记录。
- 结构化输出解析。
- Prompt 注入防护和输入边界。
- 日志脱敏。

### 安全要求

- API Key 只从环境配置读取，不进入数据库响应、日志、前端或 Git。
- `.env.example` 只能提供占位符。
- Fake/降级输出必须明确标记，不能冒充真实模型响应。
- 测试不得访问真实外网或消耗真实模型额度。

### P0 与 P1

- P0：后端 Prompt 版本、模型网关、结构化解析、记录和测试。
- P1：Prompt 配置管理页面、成本看板和在线 Prompt 对比。

### 验收

- 切换模型实现不修改业务 Service。
- Schema 错误、超时和重试均可测试。
- 每个分析结果能关联 Prompt 与模型版本。

### 建议提交拆分

```text
feat: add versioned prompt management
feat: add structured model gateway
feat: record model invocation metrics
test: cover model gateway failures
docs: document prompt and model configuration
```

---

## Step 11：商品内容生成与质量检查循环

| 项目 | 内容 |
| --- | --- |
| 目标 | 真实实现多语言商品内容生成、事实检查和合规检查 |
| 依赖 | Step 10；成员二商品/SKU事实接口 |
| MVP | 输入商品事实和目标语言，输出通过校验的结构化内容或明确失败 |

### 输出内容

- 标题。
- 核心卖点。
- 商品详情。
- FAQ。
- SKU 描述。
- 搜索关键词。
- 多语言版本。

### 检查内容

- 标题长度。
- 关键词覆盖。
- 敏感词和禁止词。
- 夸大宣传。
- 商品事实一致性。
- SKU、尺寸、材料、单位和价格事实。
- 信息完整度。
- 本地化表达。

### LangGraph Loop

```text
读取商品事实
→ 生成结构化内容
→ Pydantic Schema 校验
→ 事实一致性检查
→ 合规检查
→ 通过：返回候选版本
→ 不通过且未达上限：带问题清单重新生成
→ 达到上限：返回明确失败和未解决问题
```

### 必须测试

- 每种目标语言。
- 缺少商品事实。
- 超长标题、禁用词、夸大表达。
- 模型擅自改变材料、尺寸、数量或 SKU。
- 非法 JSON 和字段缺失。
- 重试成功、达到最大次数、模型超时。
- 相同输入的版本和审计信息。

### 验收

- 工作流真实存在 Branch/Loop，不用固定结果伪装。
- 模型输出不能绕过 Schema 和质量检查。
- 失败时不保存为通过版本。
- 商品事实和生成内容差异可追踪。

### 建议提交拆分

```text
feat: implement localized listing generation
feat: add listing fact and compliance checks
feat: add bounded content generation workflow
test: cover content generation quality loop
```

---

## Step 12：内容 Service、API、Tool、版本和确认流程

| 项目 | 内容 |
| --- | --- |
| 目标 | 对外提供完整内容生成、编辑、版本比较和草稿保存能力 |
| 依赖 | Step 1、Step 11 |
| MVP | 可生成候选内容、人工编辑、比较版本并通过确认保存草稿 |

### API 与 Tool

- 读取商品事实。
- 创建内容生成任务。
- 查询任务和生成结果。
- 单项重新生成。
- 合规检查。
- 内容版本列表和详情。
- 版本对比。
- 恢复历史版本。
- 创建商品内容草稿待确认任务。
- Tool：
  - `generate_localized_listing`
  - `check_listing_compliance`
  - `create_product_draft` 或对应功能实现时确认的统一名称

### 状态和幂等

- DRAFT、VALIDATING、PASSED、FAILED、ARCHIVED 等状态以公共枚举评审为准。
- 保存版本和恢复版本是业务写操作，必须按确认规则执行。
- 重复确认不得创建重复版本。
- 乐观锁或版本号避免覆盖其他成员修改。

### 测试

- 生成、重新生成、人工编辑、比较、恢复。
- 写操作确认前后。
- 幂等确认和并发版本冲突。
- 未通过合规检查时禁止保存为可用草稿。

### 验收

- 所有写入都有任务、确认和操作记录。
- API 文档与前端类型一致。
- 不直接调用 `MockShopeeAdapter`。

### 建议提交拆分

```text
feat: add content generation service and api
feat: add content tools and version history
feat: add confirmed content draft operations
test: cover content api and version conflicts
docs: document content generation api
```

---

## Step 13：内容工坊与多语言版本对比前端

| 项目 | 内容 |
| --- | --- |
| 目标 | 完成负责人表第 50—57 项 |
| 依赖 | Step 12 |
| MVP | 用户可以完整完成“选择商品 → 生成 → 检查 → 编辑 → 对比 → 保存草稿” |

### 页面功能

- 商品、站点、语言、受众、卖点和关键词配置。
- 标题、卖点、详情、FAQ、SKU 描述分区展示。
- 生成进度和工作流节点。
- 多语言切换及并排对比。
- 关键词、长度、敏感词、夸大和事实检查结果。
- 单项重新生成。
- 人工编辑和未保存提示。
- 版本列表、差异对比和历史恢复。
- 创建草稿待确认任务。
- 失败原因、最大重试提示和后端未连接。

### 前端测试

- 表单验证。
- 生成成功、失败、重试和取消。
- 单项重新生成。
- 合规问题定位。
- 人工编辑脏状态。
- 版本对比和恢复确认。
- 后端错误和响应式。

### 验收

- 页面不硬编码生成结果。
- 真实调用 API 并展示后端状态。
- 复用组件和设计变量，与现有 Dashboard 风格一致。
- 全套前端命令通过。
- 完成后提醒本人在负责人表第 50—57 项填写“李紫嫣”。

### 建议提交拆分

```text
feat: add content workshop api client
feat: implement localized content workshop
feat: add content version comparison
test: cover content workshop workflows
```

---

## Step 14：AI 评估体系与失败案例库

| 项目 | 内容 |
| --- | --- |
| 目标 | 用可复现数据证明 AI 能力质量，不只展示几个成功截图 |
| 依赖 | Step 2、Step 5、Step 8、Step 11 |
| MVP | 一条命令运行固定评估集并生成可审查报告 |

### 评估数据集

- 使用模拟数据构造固定、版本化的测试样本。
- 建立人工期望标签或规则期望。
- 区分开发集、回归集和演示样例。
- 不提交真实用户或店铺数据。

### 指标

- 选品计算正确率和排序稳定性。
- 评论情感、主题和痛点识别。
- 证据引用有效率。
- 内容结构化输出成功率。
- 商品事实一致率。
- 合规问题检出率。
- 幻觉率。
- 多语言人工评分。
- 重复运行稳定性。
- 响应时间、Token 和估算成本。
- Prompt 版本对比。

### 失败案例

- 输入。
- 期望输出。
- 实际输出。
- 模型/Prompt 版本。
- 失败类型。
- 是否已修复。
- 回归测试 ID。

### 验收

- 报告来自实际测试运行，不手写伪造通过率。
- 指标计算脚本和样本可审查。
- 评估失败不会被隐藏。
- 模型不可用时，确定性算法和 Fake Model 测试仍可运行。

### 建议提交拆分

```text
test: add member three ai evaluation dataset
test: add ai quality evaluation pipeline
docs: add ai evaluation report
```

---

## Step 15：成员三全链路联调与质量加固

| 项目 | 内容 |
| --- | --- |
| 目标 | 验证成员三模块不是孤立功能，而是完整进入 SellPilot 业务闭环 |
| 依赖 | Step 4、7、9、13、14；成员一、二相关模块可用 |
| MVP | 两条核心闭环在全新环境可重复运行 |

### 必须打通的闭环

#### 闭环 A：选品与产品改良

```text
市场数据
→ 智能选品
→ 商品对比
→ 评论分析
→ 产品改良建议
→ 工厂报告
→ 创建改良内容草稿待确认任务
```

#### 闭环 B：商品内容

```text
商品事实
→ 多语言内容生成
→ Schema 校验
→ 事实检查
→ 合规检查
→ 人工编辑
→ 版本对比
→ 待确认
→ 保存商品草稿
```

### 联调检查

- API 统一响应、分页和错误码。
- 数据库从零迁移。
- Mock 数据初始化。
- 任务、步骤、工具调用和确认记录。
- 重复确认保护。
- 页面加载、空、错误、超时和后端未连接。
- 模型失败和离线降级。
- 日志脱敏。
- 报告导出。
- 前后端全量测试和构建。

### 验收命令

后端：

```powershell
cd backend
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

前端：

```powershell
cd frontend
npm run format:check
npm run lint
npm run typecheck
npm run test:run
npm run build
```

仓库：

```powershell
git status
git diff --check
```

### 验收

- 全新环境按文档可以启动。
- 两条闭环都使用真实代码路径和正式 API。
- 不依赖开发者机器上的绝对路径。
- 失败路径也可演示和追踪。

### 建议提交拆分

```text
fix: resolve member three integration issues
test: add member three end to end coverage
docs: add member three integration verification
```

> 集成阶段发现的问题按主题提交；不要使用一个超大的 `fix: final update`。

---

## Step 16：技术文档、仓库外软著整理与最终交付

| 项目 | 内容 |
| --- | --- |
| 目标 | 完善仓库技术文档，并在仓库外单独整理与代码版本一致的软著材料 |
| 依赖 | Step 15 全链路验收通过 |
| MVP | 仓库内技术文档可审查；仓库外软著材料包可单独交付且未进入 Git |

### 技术文档

- 智能选品指标、公式、权重和数据限制。
- 评论分类体系和证据规则。
- 产品改良建议与报告结构。
- 商品内容生成工作流和合规规则。
- Prompt/模型配置和结构化 Schema。
- 成员三 API 和 Tool 文档。
- AI 评估方法和报告。
- 演示数据与真实数据边界。
- 运行、测试和故障排查。

### 软著材料（仅在仓库外整理）

> 软著申请表、权属资料、源码材料包、操作说明书成品、申请截图、开发者信息和补正文件不得放入 SellPilot 仓库，也不得通过 Git 分支或 Pull Request 提交。应存放在仓库外的团队受控目录中，并单独备份、审查和交付。

- 软件名称、简称和版本。
- 功能说明。
- 操作说明书。
- 源码材料。
- 系统截图。
- 开发完成日期。
- 著作权人和开发者信息。
- 权属材料和补正记录。
- 敏感信息检查记录。

如果这些材料被误复制到仓库工作区，应在暂存前移出仓库并重新检查 `git status`；不能依靠“先提交、之后再删除”的方式处理。

### 一致性检查

- 页面名称与需求一致。
- 软件名称和版本在代码、README、PPT 和仓库外软著材料中一致。
- 截图只使用模拟数据。
- 截图不包含本地路径、Token、真实姓名以外的敏感信息或调试工具。
- 文档不宣称真实 Shopee 已接入。
- 测试报告只填写实际运行结果。

### 负责人表最终检查

仅当功能和测试真正完成后，在《跨境电商AI平台前端页面负责人安排.xlsx》填写：

- 第 31—36 项：智能选品。
- 第 37—43 项：评论与产品改良。
- 第 50—57 项：内容工坊。

“完成情况”填写“李紫嫣”。不能因为页面有静态布局就提前标记完成。

### 建议提交拆分

```text
docs: complete member three technical documentation
docs: add member three user operation guide
docs: finalize member three delivery documentation
```

以上提交只包含适合进入代码仓库的技术文档，不包含软著申请材料或线下交付包。

---

## 7. 每一步统一完成定义

一个 Step 只有同时满足以下条件才算完成：

- [ ] 功能范围全部实现，没有用 TODO、静态数据或空壳代替核心逻辑。
- [ ] 正常、空数据、错误、超时和边界情况有处理。
- [ ] 输入和输出 Schema 完整。
- [ ] 写操作通过确认流程。
- [ ] 必要的 Alembic 迁移存在且可回滚。
- [ ] 单元、Service、API 或前端测试与风险匹配。
- [ ] 相关需求、架构、API、测试或操作文档已同步。
- [ ] 代码格式、静态检查、测试和构建通过。
- [ ] `git diff --check` 通过。
- [ ] `git status` 中没有无关文件、缓存、密钥或构建产物。
- [ ] PR 描述包含修改、未修改、测试、截图/接口示例、风险和影响。
- [ ] 经评审后合入 `develop`。
- [ ] 如果完成前端任务，提醒本人更新负责人 Excel。

---

## 8. 本人手动执行的 Git 标准流程

> 以下命令由本人执行。Codex 只提供建议和检查结果，不执行建分支、commit、push、PR、Tag 或远程仓库操作。

### 8.1 开始任务前

```powershell
git status
git switch develop
git pull --ff-only origin develop
git branch --list
git branch -r
git switch -c feature/具体模块-具体任务
git push -u origin feature/具体模块-具体任务
```

文档任务使用：

```powershell
git switch -c docs/具体文档
```

Bug 修复使用：

```powershell
git switch -c fix/具体问题
```

### 8.2 开发过程中

每次提交前：

```powershell
git status
git diff
git add <本次主题相关文件>
git diff --cached --check
git diff --cached
```

如果包含新建且尚未跟踪的文件，普通 `git diff` 不会显示其内容；应先直接打开检查文件，再暂存并使用 `git diff --cached` 审查完整差异。

确认暂存区只包含当前主题后：

```powershell
git commit -m "feat: implement specific feature"
git push
```

禁止使用：

```text
update
修改一下
final
完成
feat: frontend
feat: my work
```

### 8.3 准备 Pull Request

先在功能分支同步最新 `develop`：

```powershell
git fetch origin
git merge origin/develop
```

如有冲突，在当前功能分支解决，然后执行完整检查：

```powershell
git status
git diff --check
```

按改动范围运行后端、前端或全量测试。测试通过后：

```powershell
git push
```

Pull Request 必须选择：

```text
base: develop
compare: 当前短期分支
```

### 8.4 PR 描述模板

```markdown
## 修改内容

- （填写修改内容）

## 未修改内容

- （填写未修改内容）

## 测试结果

- [ ] 后端格式检查
- [ ] 后端静态检查
- [ ] 后端测试
- [ ] 前端格式检查
- [ ] 前端 Lint
- [ ] 前端类型检查
- [ ] 前端测试
- [ ] 前端构建
- [ ] git diff --check

## 页面截图或接口示例

- （填写截图或接口示例）

## 已知问题与风险

- （填写已知问题与风险）

## 对其他模块的影响

- （填写对其他模块的影响）
```

### 8.5 PR 合并后

```powershell
git switch develop
git pull --ff-only origin develop
git branch -d feature/具体模块-具体任务
git push origin --delete feature/具体模块-具体任务
```

文档或修复分支将前缀替换为实际名称。

### 8.6 Tag 规则

- 当前 Step 开发期间不创建 Tag。
- Tag 只在已验证并合入 `main` 的稳定里程碑提交上创建。
- 不在功能分支或 `develop` 上打 Tag。
- 已推送 Tag 不得移动。
- 是否创建 `v0.3.0` 由团队在完整测试和里程碑评审后决定。
- 当前有效书面规则指定组长执行 Tag，成员三不自行创建或推送 Tag。
- 如果团队正式调整执行人，应先通过 PR 更新 `docs/git-workflow.md`，并以更新后的规则为准。

---

## 9. 当前这份计划文档的手动提交步骤

由于文档生成时工作区位于 `develop`，请先创建文档分支，未提交修改会随工作区保留：

```powershell
git status
git switch -c docs/member3-implementation-plan
git status
```

直接打开并检查新文档内容：

```powershell
Get-Content -Raw -Encoding utf8 docs/plans/member3-implementation-plan.md
```

暂存并再次核对：

```powershell
git add docs/plans/member3-implementation-plan.md
git diff --cached --check
git diff --cached
```

确认内容无误后由本人提交和推送：

```powershell
git commit -m "docs: add member three implementation plan"
git push -u origin docs/member3-implementation-plan
```

然后创建 Pull Request：

```text
base: develop
compare: docs/member3-implementation-plan
```

本计划是文档变更，不创建 Tag。

---

## 10. 关键风险与预防措施

| 风险 | 预防措施 |
| --- | --- |
| 成员二接口未稳定导致返工 | 每个功能 Step 开始前检查最新 `develop`；成员三依赖稳定抽象且不直接绑定 CSV |
| 多人修改公共文件冲突 | 公共枚举、路由、依赖和组件接口先评审；小步 PR |
| LLM 直接决定评分 | 评分完全由确定性算法完成，LLM 只解释 |
| AI 编造评论证据 | 输出仅允许引用输入 review ID，校验不存在的 ID |
| 商品文案改变事实 | 生成后执行事实一致性检查，不通过不保存 |
| 模型不可用影响演示 | Fake Model 用于测试；离线降级明确标识且不冒充真实调用 |
| 写操作绕过审批 | 统一走内部 Service 和 ConfirmationTask |
| 页面做完但接口是假数据 | 完成定义要求正式 API、错误状态和测试全部通过 |
| 前端风格不一致 | 复用 Sp 组件、设计变量和现有响应式规则 |
| Excel 提前标记完成 | 只有对应功能、测试和构建均通过后填写名字 |
| 大提交难评审 | 一个分支一个任务，一个提交一个主题 |
| 将敏感信息提交 | 提交前审查暂存区、`.gitignore`、日志和截图 |
| 只为答辩做演示脚本 | 所有演示动作必须经过真实 Service/API/Workflow |
| 代码与文档不一致 | 每个 Step 同步需求、架构、API 和测试文档 |

---

## 11. 最终验收清单

### 智能选品

- [ ] 条件配置完整。
- [ ] 利润和风险计算正确。
- [ ] 分项评分和总分可解释。
- [ ] 评分不由 LLM 直接生成。
- [ ] 商品对比和报告可用。
- [ ] 数据不足和 Mock 来源明确。

### 评论与产品改良

- [ ] 六种语言处理。
- [ ] 情感、主题、痛点和趋势可用。
- [ ] 每个结论有证据评论。
- [ ] 改良建议含频率、严重度、优先级和置信度。
- [ ] 工厂报告可导出。
- [ ] 创建改良草稿经过确认。

### 商品内容

- [ ] 标题、卖点、详情、FAQ 和 SKU 描述。
- [ ] 多语言翻译和本地化。
- [ ] 关键词优化。
- [ ] 长度、敏感词、夸大和事实检查。
- [ ] 有限重试 Loop。
- [ ] 人工编辑、版本对比和历史恢复。
- [ ] 保存草稿经过确认。

### AI 工程

- [ ] Prompt 有版本。
- [ ] 输出有 Schema。
- [ ] 模型调用有超时、重试、Token、耗时和错误记录。
- [ ] 有 Fake Model 自动化测试。
- [ ] 有固定评估集、指标和失败案例。
- [ ] API Key 不进入 Git、日志或前端。

### 工程质量

- [ ] Alembic 迁移可升降级。
- [ ] 后端格式、静态检查和测试通过。
- [ ] 前端格式、Lint、类型、测试和构建通过。
- [ ] 两条核心闭环端到端通过。
- [ ] 仓库技术文档与版本一致。
- [ ] 仓库外软著材料已单独整理，且未出现在 `git status`、暂存区或提交历史中。
- [ ] 负责人表对应完成项已填写“李紫嫣”。
- [ ] PR 全部合入 `develop`。
- [ ] 是否创建里程碑 Tag 由团队在 `main` 合并前确认，并由组长按当前有效 Git 规则执行。

---

## 12. 执行纪律

后续每开始一个 Step，先执行：

1. 回顾上一 Step 的实际完成内容和遗留问题。
2. 拉取最新 `develop` 并由本人创建当前任务短期分支。
3. 复核本 Step 的依赖是否已合入，而不是只存在于队友本地。
4. 明确本 Step 的输入、输出、文件、测试和验收标准。
5. 先完成后端 Schema、Service/API 或算法，再接页面；测试可使用明确的测试替身，不写会伪装成正式能力的临时假接口。
6. 开发中保持小而清晰的主题提交。
7. 完成后运行适用的全套检查。
8. 更新相关文档和 PR 说明。
9. PR 合入 `develop` 后再开始下一 Step。
10. 前端任务完成后提醒本人更新负责人 Excel，不能遗漏，也不能提前填写。

如果发现需求、接口或团队分工发生变化，应先更新实施计划及受影响的正式架构/API文档，再继续编码，避免以临时硬编码掩盖问题。
