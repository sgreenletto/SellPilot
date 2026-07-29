# Testing

- `assistant-workflow-integration-audit.md`: develop baseline audit, Capability
  matrix, blockers, and integration decision.
- `member3-ai-evaluation.md`：成员三固定合成数据、指标与失败案例评估方法。
- `member3-ai-evaluation-report.md`：由评估命令实际生成的最新报告。
- `member3-integration-verification.md`：成员三两条核心业务闭环的联调验收。
- `tool-execution-runtime.md`: unified runtime, confirmation, MCP and migration tests.
- `task-workflow-runtime.md`: TaskRunner, step, confirmation recovery, concurrency,
  Selection/Review Analysis compatibility and migration tests.
- `inventory-replenishment-agent.md`: member-two inventory demand calculation,
  Task API integration, store isolation and frontend acceptance.

本目录用于后续维护测试策略、测试分层、测试数据规则和质量门槛。

公共后端底座已建立 pytest、pytest-asyncio、httpx 和 Ruff 配置，详细说明见 `backend-foundation.md`。测试使用隔离 PostgreSQL 与合成数据，不访问真实平台、模型、开发数据库或生产数据库。

成员二模拟业务数据的迁移、全量导入、幂等和拒绝非模拟数据测试见 `commerce-data-foundation.md`。

成员三分析、评论、改良、内容、Prompt、模型调用和报告持久化测试见 `analysis-persistence.md`。

智能选品利润、评分、缺失数据和稳定排序单元测试见 `selection-scoring.md`。

智能选品 Service、持久化、结构化 Tool、解释校验与导出测试见 `selection-api-tools.md`。

智能选品前端 API、工作台状态、表单边界和错误状态测试见 `selection-workbench.md`。

评论分析多语言预处理、结构化模型失败边界、证据与趋势测试见 `review-analysis-core.md`。

评论分析 Service、API、Tool、工作流、幂等、批处理和失败状态测试见
`review-analysis-service.md`。

产品改良报告、证据、人工状态、导出、确认幂等和确认后草稿测试见
`product-improvement-workflow.md`。

商品内容生成 Schema、质量循环、工具注册、统一认证客户端和确认写入边界测试见
`content-generation-workflow.md`。
