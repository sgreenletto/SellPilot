# Architecture

- `tool-execution-runtime.md`: unified ToolRegistry, ToolExecutor, confirmation,
  audit, retry and MCP runtime.

本目录用于记录系统上下文、模块边界、数据流、部署视图和架构决策。

当前架构约束：

- 首版为单用户、单模拟店铺。
- 平台能力通过适配器接口隔离。
- `MockShopeeAdapter` 仅用于模拟商品、订单、库存、物流和消息能力。
- 保留 `RealShopeeAdapterStub` 的设计位置，但不得宣称已接入真实 Shopee。
- 业务代码不得直接依赖 `MockShopeeAdapter` 的具体实现。
- 后端业务逻辑不得堆放在 API 路由中。
- AI 输出必须使用结构化 Schema 并经过校验。
- 所有业务写操作必须先形成待确认任务，经确认后才能执行。

公共后端底座详细设计见 `backend-foundation.md`；跨模块实体、枚举、状态和依赖方向见
`domain-contracts.md`；成员三的分析与内容持久化设计见 `analysis-persistence.md`；
智能选品确定性计算内核见 `selection-scoring.md`；成员二的数据表、单店铺映射和模拟数据
导入设计见 `commerce-data-foundation.md`；选品 Service、API、Tool 和解释工作流见
`selection-api-tools.md`；选品前端页面见 `selection-workbench.md`；评论分析领域内核见
`review-analysis-core.md`。当前已建立公共契约、
成员二/成员三持久化结构、模拟数据导入、选品确定性计算、后端应用层和选品工作台，
评论分析领域内核及 Service、分阶段 API、统一 Tool 与 AgentTask 工作流已经实现，
详见 `review-analysis-core.md` 和 `review-analysis-service.md`；评论分析页面见
`review-analysis-workbench.md`，产品改良报告与确认草稿闭环见
`product-improvement-workflow.md`。结构化商品内容生成、质量循环、模型调用记录、确认草稿、
版本历史和内容工坊见 `content-generation-workflow.md`。
