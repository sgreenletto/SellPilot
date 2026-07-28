# 成员三分析与内容持久化

## 状态与范围

本文记录成员三在公共后端底座之上增加的持久化结构，覆盖智能选品、评论分析、产品改良、商品内容、Prompt、模型调用和报告记录。

本阶段只建立 ORM 模型、Repository 和 Alembic 迁移，不包含选品评分算法、评论分析流水线、模型网关、业务 Service、API、Tool、Workflow 或前端页面。表结构存在不代表相应业务能力已经可运行。

系统仍保持单用户、单模拟店铺和 Mock Shopee 边界，不读取真实店铺数据，不连接真实 Shopee，也不调用真实模型。

## 数据边界

最新 `develop` 尚未提供商品、SKU、评论和趋势的正式数据库实体。成员三持久化结构采用以下边界：

- 成员三内部实体通过数据库外键关联。
- 来源商品、评论和趋势使用成员二模拟数据中的稳定业务 ID，例如 `PROD0001`、`REV000001`。
- 顶层分析、内容和报告记录显式保存 `source_type` 与 `is_mock_data`；来源结果和证据同时保留稳定商品/评论 ID。需要复现输入的任务还保存来源快照版本或输入条件，避免把模拟结果解释为真实经营结论。
- 业务代码后续通过成员二的 Repository、Service 或平台适配器获取来源数据，不直接读取 CSV。
- 不预先创建或假设成员二负责的商品、评论等表名，避免跨模块迁移冲突。

## 表结构

| 表 | 用途 | 关键约束 |
| --- | --- | --- |
| `product_selection_tasks` | 一次选品计算的条件、状态、来源和算法版本 | 关联创建用户，可选关联内部 AgentTask |
| `product_selection_results` | 选品排名、总分、分项指标、推荐理由、风险、完整度、来源和证据 | 同一任务内商品和排名分别唯一；排名为正；总分为 0—100；完整度为 0—1 |
| `review_analysis_results` | 一次商品评论分析的范围、输入条件、来源快照、版本、摘要和状态 | 保存来源商品 ID、站点、语言范围、来源类型和 Mock 标识 |
| `review_analysis_evidence` | 可追踪到来源评论的原文、译文、评论时间、情感、主题或痛点证据 | 保存来源与 Mock 标识；评分为 1—5；置信度为 0—1；证据身份唯一 |
| `product_improvement_reports` | 基于评论分析结果生成的改良报告版本、算法版本、数据来源和输入条件 | 同一评论分析结果内版本唯一且为正 |
| `product_improvement_suggestions` | 改良建议、频率、优先级、严重度、置信度和证据 ID | 优先级为 1—5；频率、严重度和置信度为 0—1 |
| `product_contents` | 商品、站点和目标语言对应的内容工作对象 | 商品、站点、语言组合唯一；保存来源快照、事实输入、任务关联和 Mock 标识 |
| `product_content_versions` | 标题、卖点、描述、营销文案、FAQ、SKU 内容、事实快照、变更说明和检查结果 | 同一内容对象内版本唯一且为正；历史版本不依赖可变的当前事实 |
| `prompt_templates` | Prompt 用途、任务类型、语言和生命周期 | `key` 全局唯一 |
| `prompt_versions` | 不可变 Prompt 内容、结构化 Schema、模型配置和变更说明 | 同一模板内版本和校验摘要唯一 |
| `model_invocations` | 发起用户、模型、参数、超时、重试、Token、成本、耗时、状态和脱敏输入输出摘要 | Token、重试、成本与耗时非负；超时为正；不保存 API Key |
| `generated_reports` | 可审查的结构化报告载荷、数据来源、输入条件、任务/模型调用和结果版本 | 同一来源对象的同类报告版本唯一；显式保存 Mock 标识 |

## 关系与证据链

```text
ProductSelectionTask
  └─ ProductSelectionResult

ReviewAnalysisResult
  ├─ ReviewAnalysisEvidence → source_review_id
  └─ ProductImprovementReport
       └─ ProductImprovementSuggestion → evidence_review_ids

PromptTemplate
  └─ PromptVersion
       ├─ ModelInvocation
       ├─ ReviewAnalysisResult
       ├─ ProductImprovementReport
       └─ ProductContentVersion

ProductContent
  └─ ProductContentVersion

AgentTask
  ├─ ProductSelectionTask
  ├─ ReviewAnalysisResult
  ├─ ProductContent
  ├─ ModelInvocation
  └─ GeneratedReport
```

成员三内部证据链外键使用 `ON DELETE RESTRICT`，Repository 不提供删除方法。业务层后续通过状态归档记录，不通过物理删除破坏结果、证据、Prompt 和模型调用之间的追踪关系。

## 数据类型与兼容性

- 主键使用应用侧 UUID，与公共模型保持一致。
- 时间使用带时区 `DateTime`，由应用生成 UTC 时间。
- 结构化字段使用公共 `JSON_TYPE`，在 PostgreSQL 中映射为 JSONB。
- 评分、严重度和置信度使用定点 `NUMERIC`，不使用二进制浮点保存业务结果。
- 表、索引、主键、外键和检查约束遵循公共 Alembic 命名规则。

自动化测试、迁移验证和运行环境统一使用 PostgreSQL；测试使用独立数据库，不连接开发数据。

## Repository 边界

Repository 只负责持久化和查询，当前提供：

- 选品运行与结果的创建、状态筛选、分页和排名读取。
- 评论分析运行与证据的创建、商品/状态筛选和证据分页。
- 产品改良报告与建议的创建和有序读取。
- 商品内容工作对象与版本的创建和版本历史读取。
- Prompt 模板、Prompt 版本和最新版本查询。
- 模型调用及生成报告的创建、筛选和分页。

所有可能增长的集合查询均要求显式传入页码和页大小；Repository 不提供无界列表读取。

Repository 不负责算法、AI 调用、Schema 业务校验、权限、状态机或确认流程。后续业务 Service 必须在调用写入 Repository 前执行结构化校验，并按公共规则为业务写操作创建待确认任务；不得把 Repository 直接暴露为公共创建 API。

## 迁移

迁移链：

```text
20260727_0001 public foundation
  → 20260727_0002 analysis persistence
```

正式结构只由 Alembic 维护。应用启动不调用 `create_all`；测试中的 `create_all` 仅用于逐测试隔离。
