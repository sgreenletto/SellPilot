# 公共后端架构底座

## 状态与范围

当前版本为 **0.1.0 Foundation Milestone**，只实现公共后端底座，不表示完整业务已完成或已用于生产。首版继续保持单用户、单模拟店铺和 Mock Shopee 边界。

明确不包含商品、SKU、库存、订单、物流、评论、客服、内容生成、RAG、真实 Shopee 网络调用或正式业务工作流。

## 分层

- `api/`：HTTP 协议、依赖注入和统一响应。
- `services/`：认证、任务和确认用例及状态流转。
- `repositories/`：SQLAlchemy 查询与持久化。
- `db/`：异步引擎、会话、公共模型与元数据。
- `adapters/`：平台能力抽象；业务代码只依赖 `PlatformAdapter`。
- `tools/`：结构化工具契约、风险阻断、超时和可选调用记录。
- `agents/` 与 `workflows/`：公共状态、注册器和无 LLM diagnostic 图。
- `mcp_server/`：官方 Python MCP SDK 的只读 stdio 服务。

API 路由不承载业务状态机。AgentTask 与 ConfirmationTask 只能由内部 Service 创建，不提供公共创建 API。

## 配置与安全

`Settings` 从环境变量或仓库根目录 `.env` 读取配置，并通过缓存工厂提供。
团队不得创建或分发 `backend/.env`；百炼、数据库和后端安全配置统一以根目录
`.env.example` 为模板写入本地根目录 `.env`。测试可用环境变量覆盖并清理缓存。

- `PLATFORM_ADAPTER` 只允许 `mock` 或 `real`。
- real 模式缺少明确配置时启动校验失败，不会回退到 mock。
- production 禁止示例或短 JWT 密钥。
- 日志过滤密码、Token、Authorization、JWT 和 API Key 样式内容。

## 数据库

SQLAlchemy 使用 `AsyncEngine` 与 `async_sessionmaker`。模型使用应用侧 UUID、带时区时间字段和 Alembic 命名约定。结构化字段在 PostgreSQL 中使用 JSONB。

正式数据库结构只通过 Alembic 迁移。应用启动不调用 `create_all`。测试中的 `create_all` 仅用于隔离 API/Service 测试；迁移测试独立执行完整的 upgrade、downgrade、upgrade。

应用启动、团队联调和自动化测试统一使用 `postgresql+asyncpg`。测试只操作独立的
`sellpilot_test` 数据库，不得使用开发数据库或其他数据库引擎。

## 写操作确认

公共工具对 WRITE 和 HIGH_RISK 调用强制要求确认上下文。ConfirmationService 在确认前不调用执行器；未注册执行器时保持 PENDING 并返回明确错误。执行成功或失败均保留结果，重复确认不会重复执行。

## 平台适配器

`MockShopeeAdapter` 只实现 ping 和基础能力描述，所有业务方法抛出统一未实现异常。`RealShopeeAdapterStub` 永远不发起网络请求，ping 返回未配置，业务方法抛出平台未配置异常。

## LangGraph 与 MCP

diagnostic 工作流使用 `StateGraph` 验证 State 传递、条件分支和有界重试，不接入 LLM，不消耗模型 Token，也不是正式业务工作流。

MCP 基于锁定的 `mcp 1.28.1`，使用 `mcp.server.fastmcp.FastMCP` 和默认 stdio transport，仅暴露只读 `system_health`。
