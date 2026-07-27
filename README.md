# SellPilot

SellPilot 是面向跨境电商卖家的 AI 运营辅助平台，首版以 Shopee 业务场景进行验证。

## 当前状态

**Public Backend Foundation / 0.1.0.dev0**

当前已完成公共后端架构底座。这是开发版本，不表示 `v0.1.0` 已发布；具体跨境电商业务和前端仍未实现。

## 核心业务闭环

- 市场数据 → 智能选品 → 评论分析 → 产品改良
- 商品资料 → 多语言内容 → 检查 → 草稿 → 模拟上架
- 买家消息 → 意图识别 → RAG / 业务工具 → 回复 → 人工处理

上述闭环仍是后续业务规划，不属于当前底座完成范围。

## 首版边界

- 单用户模式。
- 仅一个模拟店铺。
- 不连接真实 Shopee 账号。
- `MockShopeeAdapter` 当前只实现基础状态，业务方法明确未实现。
- `RealShopeeAdapterStub` 不发起网络请求，不代表已接入真实 Shopee。
- 所有业务写操作必须先进入待确认任务。

## 技术栈

| 范围 | 选型与状态 |
| --- | --- |
| 前端 | 计划采用 Vue 3、TypeScript、Vite；尚未初始化 |
| 后端 | Python 3.12、FastAPI、Pydantic v2 |
| 数据库 | SQLAlchemy 2 异步模式、Alembic；目标 PostgreSQL |
| 认证 | PyJWT、pwdlib Argon2 |
| AI 编排 | LangGraph；当前只有无 LLM diagnostic 工作流 |
| MCP | 官方 Python MCP SDK；当前只有只读 `system_health` |
| 平台集成 | 平台适配器接口；Mock 基础状态与 Real Stub |

## 顶层目录

| 路径 | 用途 |
| --- | --- |
| `.github/` | Issue 与 Pull Request 模板 |
| `backend/` | 公共后端底座、迁移与测试 |
| `frontend/` | 前端工程占位，尚未初始化 |
| `data/` | 原始、处理、演示数据及模板目录约定 |
| `docs/` | 需求、架构、API、测试、部署和 Git 工作流文档 |
| `scripts/` | 后续开发、检查和运维脚本占位 |

## 当前已实现

- 缓存式 Settings、环境校验和安全配置边界。
- 统一 API 响应、异常转换、Request ID 和标准日志脱敏。
- SQLAlchemy 异步会话、六个公共模型和可逆 Alembic 初始迁移。
- 单用户登录、当前用户和修改密码接口，以及交互式管理员 CLI。
- 内部任务和待确认任务状态机、分页查询与幂等确认。
- 平台适配器抽象、Mock 基础状态和非联网 Real Stub。
- 结构化工具注册器、风险阻断、超时与可选 ToolCall 记录。
- 只读 MCP `system_health`。
- 无 LLM 的 diagnostic LangGraph 与公共工作流注册器。
- 隔离 SQLite 测试和 Ruff 配置。

安装、迁移、启动、管理员创建及验证命令见 `backend/README.md`。

## 当前尚未实现

- Vue 3 / Vite 前端项目及页面。
- 商品、SKU、库存、订单、物流、消息或客服业务模型。
- 市场数据、智能选品、评论分析和产品改良。
- 多语言内容生成、商品草稿和模拟上下架。
- RAG 知识库、正式 AI Agent 或业务工作流。
- Mock Shopee 完整业务数据和业务方法。
- 真实 Shopee 认证、网络请求或平台连接。
- Docker Compose、生产部署配置和 CI/CD。

## 分支

- `main`：稳定发布分支。
- `develop`：日常集成开发分支。

功能与修复分支的完整约定见 `docs/git-workflow.md`。

## 安全

禁止提交 `.env`、API Key、Token、数据库密码、真实用户数据或真实店铺数据。配置示例只能包含安全占位符，日志、截图和演示数据必须脱敏。
