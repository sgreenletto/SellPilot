# SellPilot

SellPilot 是面向跨境电商卖家的 AI 运营辅助平台，首版以 Shopee 模拟业务作为验证场景。

## 当前版本

**v0.1.0 — Foundation Milestone**

v0.1.0 表示 SellPilot 的公共后端、前端框架和工程质量基线已经建立，可用于后续业务分支开发；它不是最终项目版本，不表示完整跨境电商业务已经完成，也不代表系统已用于生产环境。

该里程碑采用普通 Git Tag 标记，不创建 GitHub Release。本仓库当前仍保持单用户、单模拟店铺和 Mock Shopee 模式，不连接真实 Shopee 账号。

## 目标业务闭环

- 市场数据 → 智能选品 → 评论分析 → 产品改良
- 商品资料 → 多语言内容 → 检查 → 草稿 → 模拟上架
- 买家消息 → 意图识别 → RAG / 业务工具 → 回复 → 人工处理

以上是项目目标闭环；v0.1.0 只提供承载这些能力的公共底座。

## v0.1.0 已实现

### 后端

- FastAPI 公共架构、Pydantic Settings 和标准日志。
- 统一响应、统一异常、参数校验转换和 `X-Request-ID`。
- SQLAlchemy 2 异步会话、PostgreSQL 目标配置和 SQLite 隔离测试。
- Alembic 迁移及完整 upgrade / downgrade 基础迁移。
- 单用户认证底座、Argon2 密码哈希、Bearer JWT 和管理员 CLI。
- 六张公共基础表：User、AgentTask、AgentTaskStep、ToolCall、ConfirmationTask、OperationLog。
- `PlatformAdapter`、基础状态可用的 `MockShopeeAdapter` 和非联网 `RealShopeeAdapterStub`。
- 结构化 `ToolRegistry`、风险确认阻断、超时与可选 ToolCall 记录。
- 官方 Python MCP SDK 的只读 `system_health`。
- LangGraph 公共 State、工作流注册器和不调用 LLM 的 diagnostic 工作流。
- Task 和 Confirmation 状态流转、幂等确认及自动化测试。

### 前端

- Vue 3、TypeScript、Vite、Vue Router 和 Pinia。
- SellPilot 语义设计变量、`Sp*` 可复用组件库和 Element Plus 基础能力。
- 大圆角应用 Shell、侧边栏、顶部栏和响应式独立滚动布局。
- 使用 ECharts 的经营看板和原创本地 SVG/CSS AI Orb。
- 开发环境设计系统展示页。
- 业务模块统一占位路由。
- 平台状态 API 客户端；后端不可达时明确显示“后端未连接”。
- Vitest、Vue Test Utils、ESLint、Prettier 和严格 TypeScript 检查。

Dashboard 使用带稳定 ID 的合成 Mock 数据，不是实际店铺、商品、订单或用户数据。除 Dashboard 和开发环境设计系统页外，当前业务页面主要是占位页面。

## 当前未实现

- 完整市场数据业务和正式智能选品算法。
- 评论分析、产品改良和正式商品内容生成。
- 商品、SKU、库存、订单、物流和客服完整业务。
- RAG 知识库和正式业务 Agent。
- 完整 Mock Shopee 商品、订单、库存、物流和消息数据。
- 真实 Shopee 认证、密钥读取或网络调用。
- 多用户、多角色和多店铺。
- Docker Compose、CI/CD 和生产部署。

## 系统分层

```text
Vue Views
  → Sp 公共组件 / Pinia / composables
  → 统一 HTTP 客户端
  → FastAPI API
  → services
  → repositories / workflows / tools / adapters
  → SQLAlchemy / MCP / LangGraph
```

- API 路由只负责协议转换、校验和调用应用层。
- 业务代码只依赖 `PlatformAdapter`，不直接依赖 Mock 具体实现。
- 正式数据库结构只通过 Alembic 管理。
- 写操作必须经过待确认任务。

## 仓库目录

| 路径 | 用途 |
| --- | --- |
| `.github/` | Issue 与 Pull Request 模板 |
| `backend/` | FastAPI 公共底座、迁移、CLI 和测试 |
| `frontend/` | Vue 前端、组件库、Dashboard 和测试 |
| `data/` | 原始、处理、演示数据及模板目录约定 |
| `docs/` | 需求、架构、API、测试、部署和 Git 工作流 |
| `scripts/` | 后续检查和运维脚本目录 |

## 后端开发

要求 Python 3.12 和 uv。在 `backend` 目录执行：

```powershell
uv sync
uv run alembic upgrade head
uv run uvicorn sellpilot.main:app --host 127.0.0.1 --port 8000
```

交互式创建单用户管理员：

```powershell
uv run sellpilot-create-admin --username admin
```

后端验证：

```powershell
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

## 前端开发

在 `frontend` 目录执行：

```powershell
npm install
npm run dev -- --host 127.0.0.1
```

前端验证与构建：

```powershell
npm run format:check
npm run lint
npm run typecheck
npm run test:run
npm run build
```

## Windows 一键启动

首次运行前仍需按后端和前端章节安装依赖。依赖准备完成后，可双击根目录的
`start-sellpilot.bat`，脚本会分别打开后端和前端开发服务窗口，并打开
`http://127.0.0.1:5173`。

只检查 `uv`、`npm`、项目文件和前端依赖是否就绪而不启动服务：

```powershell
.\start-sellpilot.bat --check
```

## 环境变量

根目录 `.env.example` 提供后端安全占位符，至少包括应用环境、数据库、JWT、日志和平台适配器配置。复制为本地 `.env` 后填写，不得提交 `.env`。

前端读取：

- `VITE_API_BASE_URL`：浏览器 API 基础路径，开发默认 `/api`。
- `VITE_PROXY_TARGET`：Vite 开发代理目标，示例为 `http://127.0.0.1:8000`。

`VITE_*` 会暴露给浏览器，禁止存放密码、Token 或 API Key。`PLATFORM_ADAPTER=real` 缺少明确配置时会失败，不会回退到 mock。

## 页面路由

- `/dashboard`：经营看板。
- `/assistant`：AI 运营助手占位页。
- `/market/data`、`/market/selection`、`/market/reviews`：市场与选品占位页。
- `/products`、`/products/content`、`/products/listing-inventory`：商品运营占位页。
- `/customer-service/conversations`、`/customer-service/knowledge`：智能客服占位页。
- `/orders`：订单与履约占位页。
- `/tasks`：任务中心占位页。
- `/dev/design-system`：仅开发环境注册的设计系统展示页。

## 当前基础 API

所有 API 位于 `/api/v1`：

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`
- `GET /api/v1/platform/status`
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `GET /api/v1/confirmations`
- `GET /api/v1/confirmations/{confirmation_id}`
- `POST /api/v1/confirmations/{confirmation_id}/confirm`
- `POST /api/v1/confirmations/{confirmation_id}/cancel`

Task 和 Confirmation 只能由内部 Service 创建，不提供公共创建 API。

## Git 工作流

- `main`：稳定发布分支。
- `develop`：日常集成分支。
- 一个可验收任务创建一个短期 `feature/*`、`fix/*` 或 `docs/*` 分支，不建立成员个人永久分支。
- 所有分支合并必须通过 Pull Request；普通任务 PR 合并到 `develop`，合并后删除短期分支。
- 只有达到明确发布里程碑时，才通过 PR 将 `develop` 合并到 `main`。
- Tag 只能由组长在 `main` 的已测试提交上创建；已推送 Tag 不得移动，出现问题时增加 Patch 版本。
- v0.1.0 只使用普通 Git Tag，不创建 GitHub Release；最终完整版本目标为 v1.0.0。

完整规范见 `docs/git-workflow.md`。

## 安全边界

- 禁止提交 `.env`、API Key、Token、数据库密码、真实个人信息或真实店铺数据。
- `RealShopeeAdapterStub` 不进行网络请求，不代表真实 Shopee 已接入。
- 日志、测试、截图和 Dashboard 数据必须使用合成内容或脱敏内容。
- 不得绕过适配器、结构化 Schema、服务层或确认流程。

## 文档索引

- `backend/README.md`：后端安装、迁移、运行与边界。
- `frontend/README.md`：前端命令、路由、组件和设计系统约束。
- `docs/architecture/backend-foundation.md`：后端分层与安全设计。
- `docs/architecture/frontend-foundation.md`：前端分层与响应式设计。
- `docs/api/foundation-api.md`：公共 API 契约。
- `docs/frontend/design-system.md`：设计变量和公共组件规范。
- `docs/testing/backend-foundation.md`：后端测试策略。
- `docs/testing/frontend-foundation.md`：前端测试与浏览器验收。
- `docs/git-workflow.md`：分支、提交和发布流程。
