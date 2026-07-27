# 公共领域契约

## 1. 状态与边界

本文冻结 SellPilot 第一阶段跨模块共享的领域名称、字段语义、状态值和依赖方向。当前代码基线仍是 `v0.1.0 Foundation Milestone`：单用户、单模拟店铺、`MockShopeeAdapter`，不连接真实 Shopee。

本轮在代码中实现的是公共枚举、Schema、响应契约和 Task/Confirmation 状态校验。下列业务实体均为公共字段契约，不代表已经存在 ORM、Repository、Service 或可运行 API。现有正式数据库仍只有 User、AgentTask、AgentTaskStep、ToolCall、ConfirmationTask、OperationLog 等底座表；本轮没有创建业务表或 Alembic 迁移。

| 实体组 | 当前实现状态 | 后续负责人 |
| --- | --- | --- |
| AgentTask、ConfirmationTask、ToolCall 公共底座 | 已存在，队长维护公共状态、确认、审计和集成 | 队长 |
| MarketProduct、StoreProduct、SKU、Order、Logistics | 仅冻结契约，未实现业务表 | 成员二 |
| Review、SelectionTask、ReviewAnalysis、ImprovementReport、ContentVersion、Report | 仅冻结契约，未实现业务表 | 成员三 |
| Conversation、Message、KnowledgeDocument、KnowledgeChunk | 仅冻结契约，未实现业务表 | 成员四 |

队长不得提前建立上述完整业务表，也不得代替成员实现完整业务 Service、工作流或页面。成员实现时必须复用本文枚举与公共 Schema；正式表结构通过各自分支的 Alembic 迁移维护。

## 2. 共享约定

- 领域 ID 使用项目现有 UUID 策略；外部平台标识单独命名为 `external_*`，不得与内部 UUID 混用。
- API 时间是带时区的 ISO 8601 字符串；后端创建和比较时间使用 UTC。
- 金额采用 Decimal 语义，并与 `CurrencyCode` 一起传输；JSON 金额是十进制字符串。
- Mock 数据必须带 `SourceMetadata.is_mock=true`，不得描述为真实 Shopee 数据。
- 多语言值使用 `LocalizedText` 或 `LocalizedTextSet`，不使用任意键对象。
- JSON 扩展字段必须由模块定义具体 Pydantic Schema，不得以无约束对象替代领域模型。

## 3. 实体最小契约

### 3.1 MarketProduct

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 内部市场商品 ID | 系统 | Review、SelectionTask | 是 | 成员二 |
| external_product_id | string | 否 | 来源平台商品标识 | Adapter/导入 | 无 | 是 | 成员二 |
| site | SiteCode | 是 | 市场站点 | 来源元数据 | 无 | 是 | 成员二 |
| title | LocalizedTextSet | 是 | 原始或规范化标题 | 采集/导入 | 无 | 是 | 成员二 |
| price | Money | 否 | 可比较的展示价格 | 采集/导入 | 无 | 是 | 成员二 |
| source | SourceMetadata | 是 | 来源及 Mock 标记 | 系统 | 无 | 是 | 成员二 |
| created_at / updated_at | ISO 8601 | 是 | 审计时间 | 系统 | 无 | 是 | 成员二 |

### 3.2 StoreProduct

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 内部店铺商品 ID | 系统 | SKU、ContentVersion | 是 | 成员二 |
| external_product_id | string | 否 | Mock 平台商品标识 | PlatformAdapter | 无 | 是 | 成员二 |
| site | SiteCode | 是 | 发布站点 | 用户/任务 | 无 | 是 | 成员二 |
| status | ProductStatus | 是 | 商品生命周期状态 | Service | ConfirmationTask | 是 | 成员二 |
| title | LocalizedTextSet | 是 | 当前商品标题 | 用户/内容版本 | ContentVersion | 是 | 成员二 |
| source | SourceMetadata | 是 | 来源信息 | 系统 | MarketProduct | 是 | 成员二 |
| created_at / updated_at | ISO 8601 | 是 | 审计时间 | 系统 | 无 | 是 | 成员二 |

### 3.3 SKU

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 内部 SKU ID | 系统 | StoreProduct、Order | 是 | 成员二 |
| store_product_id | UUID | 是 | 所属店铺商品 | 系统 | StoreProduct | 是 | 成员二 |
| merchant_sku | string | 是 | 店内稳定 SKU 编码 | 用户/导入 | 无 | 是 | 成员二 |
| status | SkuStatus | 是 | SKU 可售状态 | Service | ConfirmationTask | 是 | 成员二 |
| price | Money | 是 | SKU 售价 | 用户/导入 | 无 | 是 | 成员二 |
| stock_quantity | integer | 是 | 非负库存数量 | Adapter/调整 | ConfirmationTask | 是 | 成员二 |
| created_at / updated_at | ISO 8601 | 是 | 审计时间 | 系统 | 无 | 是 | 成员二 |

### 3.4 Review

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 内部评论 ID | 系统 | ReviewAnalysis | 是 | 成员三 |
| market_product_id | UUID | 否 | 对应市场商品 | 采集/导入 | MarketProduct | 是 | 成员三 |
| rating | integer(1..5) | 是 | 星级 | 采集/导入 | 无 | 是 | 成员三 |
| content | LocalizedText | 否 | 评论正文 | 采集/导入 | 无 | 是 | 成员三 |
| reviewed_at | ISO 8601 | 否 | 原评论时间 | 来源 | 无 | 是 | 成员三 |
| source | SourceMetadata | 是 | 来源与 Mock 标记 | 系统 | 无 | 是 | 成员三 |

### 3.5 Order

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 内部订单 ID | 系统 | Logistics | 是 | 成员二 |
| external_order_id | string | 否 | Mock 平台订单号 | PlatformAdapter | 无 | 是 | 成员二 |
| status | OrderStatus | 是 | 订单状态 | Service/Adapter | ConfirmationTask | 是 | 成员二 |
| total_amount | Money | 是 | 订单总额 | Adapter/导入 | 无 | 是 | 成员二 |
| placed_at | ISO 8601 | 是 | 下单时间 | 来源 | 无 | 是 | 成员二 |
| source | SourceMetadata | 是 | 来源与 Mock 标记 | 系统 | 无 | 是 | 成员二 |
| created_at / updated_at | ISO 8601 | 是 | 审计时间 | 系统 | 无 | 是 | 成员二 |

### 3.6 Logistics

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 内部物流记录 ID | 系统 | Order | 是 | 成员二 |
| order_id | UUID | 是 | 所属订单 | 系统 | Order | 是 | 成员二 |
| status | LogisticsStatus | 是 | 履约状态 | Adapter/Service | ConfirmationTask | 是 | 成员二 |
| carrier | string | 否 | 承运方名称 | Adapter/导入 | 无 | 是 | 成员二 |
| tracking_number | string | 否 | 脱敏展示的运单号 | Adapter/导入 | 无 | 是 | 成员二 |
| shipped_at / delivered_at | ISO 8601 | 否 | 发货和签收时间 | 来源 | 无 | 是 | 成员二 |

### 3.7 Conversation

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 内部会话 ID | 系统 | Message | 是 | 成员四 |
| external_conversation_id | string | 否 | Mock 平台会话标识 | PlatformAdapter | 无 | 是 | 成员四 |
| status | ConversationStatus | 是 | 会话处理状态 | Service | ConfirmationTask | 是 | 成员四 |
| risk_level | RiskLevel | 是 | 客服业务风险，不是工具风险 | 工作流/人工 | 无 | 是 | 成员四 |
| language | LanguageCode | 否 | 当前主要语言 | 分类结果 | Message | 是 | 成员四 |
| source | SourceMetadata | 是 | 来源与 Mock 标记 | 系统 | 无 | 是 | 成员四 |
| created_at / updated_at | ISO 8601 | 是 | 审计时间 | 系统 | 无 | 是 | 成员四 |

### 3.8 Message

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 内部消息 ID | 系统 | Conversation | 是 | 成员四 |
| conversation_id | UUID | 是 | 所属会话 | 系统 | Conversation | 是 | 成员四 |
| direction | `inbound` / `outbound` | 是 | 消息方向 | Adapter/Service | 无 | 是 | 成员四 |
| content | LocalizedText | 是 | 消息正文 | 买家/草稿/人工 | ContentVersion | 是 | 成员四 |
| sent_at | ISO 8601 | 是 | 发送或接收时间 | 来源 | 无 | 是 | 成员四 |
| source | SourceMetadata | 是 | 来源与 Mock 标记 | 系统 | 无 | 是 | 成员四 |

### 3.9 KnowledgeDocument

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 知识文档 ID | 系统 | KnowledgeChunk | 是 | 成员四 |
| title | string | 是 | 安全处理后的文档标题 | 上传/导入 | 无 | 是 | 成员四 |
| language | LanguageCode | 是 | 文档主语言 | 用户/检测 | 无 | 是 | 成员四 |
| checksum_sha256 | string | 是 | 内容去重校验值 | 系统 | 无 | 是 | 成员四 |
| source | SourceMetadata | 是 | 来源信息 | 系统 | 无 | 是 | 成员四 |
| created_at / updated_at | ISO 8601 | 是 | 审计时间 | 系统 | 无 | 是 | 成员四 |

### 3.10 KnowledgeChunk

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 文档片段 ID | 系统 | KnowledgeDocument | 是 | 成员四 |
| document_id | UUID | 是 | 所属知识文档 | 系统 | KnowledgeDocument | 是 | 成员四 |
| sequence | integer | 是 | 文档内稳定顺序 | 切分服务 | 无 | 是 | 成员四 |
| content | LocalizedText | 是 | 受约束的片段文本 | 切分服务 | 无 | 是 | 成员四 |
| token_count | integer | 否 | 使用指定 tokenizer 的计数 | 切分服务 | 无 | 是 | 成员四 |
| created_at | ISO 8601 | 是 | 创建时间 | 系统 | 无 | 是 | 成员四 |

### 3.11 SelectionTask

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 选品任务 ID | 系统 | AgentTask、MarketProduct | 是 | 成员三 |
| agent_task_id | UUID | 是 | 公共长任务引用 | TaskService | AgentTask | 是 | 成员三 |
| site | SiteCode | 是 | 目标市场 | 用户 | 无 | 是 | 成员三 |
| criteria | SelectionCriteria Schema | 是 | 模块定义的结构化筛选和权重 | 用户/Service | 无 | 是 | 成员三 |
| status | TaskStatus | 是 | 执行状态 | TaskService | AgentTask | 是 | 成员三 |
| created_at / updated_at | ISO 8601 | 是 | 审计时间 | 系统 | 无 | 是 | 成员三 |

### 3.12 ReviewAnalysis

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 评论分析 ID | 系统 | Review、ImprovementReport | 是 | 成员三 |
| review_ids | UUID[] | 是 | 有界且去重的评论引用 | Service | Review | 是 | 成员三 |
| language | LanguageCode | 是 | 输出语言 | 请求 | 无 | 是 | 成员三 |
| summary | LocalizedText | 是 | 结构化分析摘要 | AI Workflow | 无 | 是 | 成员三 |
| risk_level | RiskLevel | 是 | 分析结果风险等级 | 规则/工作流 | 无 | 是 | 成员三 |
| source | SourceMetadata | 是 | 模型或规则来源 | 系统 | 无 | 是 | 成员三 |

### 3.13 ImprovementReport

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 改良报告 ID | 系统 | ReviewAnalysis、Report | 是 | 成员三 |
| review_analysis_id | UUID | 是 | 依据的评论分析 | Service | ReviewAnalysis | 是 | 成员三 |
| title | LocalizedText | 是 | 报告标题 | 工作流 | 无 | 是 | 成员三 |
| recommendations | ImprovementItem[] | 是 | 模块定义的结构化建议 | AI Workflow | 无 | 是 | 成员三 |
| content_version | integer | 是 | 内容版本号 | Service | ContentVersion | 是 | 成员三 |
| created_at | ISO 8601 | 是 | 创建时间 | 系统 | 无 | 是 | 成员三 |

### 3.14 ContentVersion

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 内容版本 ID | 系统 | StoreProduct、Message | 是 | 成员三 |
| content_type | ContentType | 是 | 内容用途 | 请求 | 无 | 是 | 成员三 |
| target_id | UUID | 是 | 所属领域对象 ID | Service | StoreProduct/Message | 是 | 成员三 |
| version | integer | 是 | 对目标和类型单调递增 | Service | 无 | 是 | 成员三 |
| content | LocalizedTextSet | 是 | 多语言内容 | AI/人工 | 无 | 是 | 成员三 |
| status | ProductStatus | 否 | 商品内容场景的发布状态 | Service | ConfirmationTask | 是 | 成员三 |
| created_at | ISO 8601 | 是 | 创建时间 | 系统 | 无 | 是 | 成员三 |

### 3.15 Report

| 字段名称 | 类型 | 必填 | 说明 | 来源 | 关联实体 | 允许 Mock | 负责成员 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| id | UUID | 是 | 报告 ID | 系统 | SelectionTask/ReviewAnalysis | 是 | 成员三 |
| report_type | ReportType | 是 | 报告类别 | 请求/工作流 | 无 | 是 | 成员三 |
| title | LocalizedText | 是 | 报告标题 | 工作流/人工 | 无 | 是 | 成员三 |
| task_id | UUID | 否 | 生成任务引用 | TaskService | AgentTask | 是 | 成员三 |
| file_id | UUID | 否 | 导出文件引用；当前未建设文件中心 | 导出 Service | 无 | 是 | 成员三 |
| source | SourceMetadata | 是 | 数据与生成来源 | 系统 | 无 | 是 | 成员三 |
| created_at | ISO 8601 | 是 | 创建时间 | 系统 | 无 | 是 | 成员三 |

## 4. 模块依赖方向

确定性业务路径：

```text
Vue 页面
→ 统一 API 客户端
→ FastAPI API
→ Service
→ Repository 或 PlatformAdapter
```

AI 编排路径：

```text
AI Workflow
→ Tool
→ Service
→ Repository 或 PlatformAdapter
```

禁止以下依赖：

```text
页面 → 数据库
Agent → 数据库
Agent → MockShopeeAdapter
API 路由 → 大量业务逻辑
Tool → 直接拼接 SQL
Service → 具体 Mock 实现
```

Service 只能依赖 `PlatformAdapter` 抽象。`MockShopeeAdapter` 只提供模拟边界，`RealShopeeAdapterStub` 只表达未接入状态，任何 real 配置错误都不得静默回退到 mock。

## 5. Agent、工具与确定性逻辑边界

- CRUD、数据清洗、导入导出和确定性评分计算是 Service/Repository 的职责，不是 Agent。
- Agent 只负责意图识别、步骤编排、条件分支、有最大重试次数的循环以及结果汇总。
- AI 输出进入 Service 前必须经过具体 Pydantic Schema 校验。
- READ 工具可直接执行；WRITE 工具必须获得 Confirmation；HIGH_RISK 工具还必须保留完整前后快照。
- Agent 不能执行最终写入。确认后的写操作由注册到 ConfirmationService 的执行器调用 Service 完成，成功和失败均记录审计信息。
