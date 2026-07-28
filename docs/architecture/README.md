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
导入设计见 `commerce-data-foundation.md`。当前已建立公共契约、成员二/成员三持久化结构、
模拟数据导入和选品纯计算能力，但尚未接入选品 Service、API、Tool、工作流或页面；
持久化结构也不表示对应业务 API、适配器操作、评论分析或内容生成已经可运行。
