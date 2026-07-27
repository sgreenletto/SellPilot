# Architecture

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

公共后端底座已建立，详细设计见 `backend-foundation.md`；跨模块实体、枚举、状态和依赖方向见 `domain-contracts.md`。当前只有公共模型、平台适配器契约和不接入 LLM 的 diagnostic 工作流；具体跨境电商业务模块仍未实现。
