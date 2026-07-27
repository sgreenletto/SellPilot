# SellPilot

SellPilot 是面向跨境电商卖家的 AI 运营辅助平台，首版以 Shopee 业务场景进行验证。

## 当前状态

**Phase 1 / Project Initialization**

当前仅完成仓库工程骨架、协作约定、文档占位和安全配置。项目尚未初始化前后端框架、安装依赖或实现业务功能，不具备可运行条件。

## 核心业务闭环

- 市场数据 → 智能选品 → 评论分析 → 产品改良
- 商品资料 → 多语言内容 → 检查 → 草稿 → 模拟上架
- 买家消息 → 意图识别 → RAG / 业务工具 → 回复 → 人工处理

## 首版边界

- 单用户模式。
- 仅一个模拟店铺。
- 不连接真实 Shopee 账号。
- 计划通过 `MockShopeeAdapter` 模拟商品、订单、库存、物流和消息能力。
- 计划保留 `RealShopeeAdapterStub` 接口位置，但不代表已接入真实 Shopee。
- 所有业务写操作计划进入待确认任务，由用户确认后执行。

## 计划技术栈

| 范围 | 计划选型 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite |
| 后端 | FastAPI、Pydantic、SQLAlchemy |
| 数据库 | PostgreSQL |
| AI 编排 | LangGraph |
| 平台集成 | 平台适配器接口；首版使用 Mock 实现 |

技术栈目前仅为规划，尚未安装或初始化。

## 顶层目录

| 路径 | 用途 |
| --- | --- |
| `.github/` | Issue 与 Pull Request 模板 |
| `backend/` | 后端工程占位 |
| `frontend/` | 前端工程占位 |
| `data/` | 原始、处理、演示数据及模板的目录约定 |
| `docs/` | 需求、架构、API、测试、部署和 Git 工作流文档 |
| `scripts/` | 后续开发、检查和运维脚本占位 |

## 当前已完成

- 建立首版目录骨架。
- 记录项目定位、范围和 Mock Shopee 边界。
- 建立贡献、分支、提交和 Agent 协作规范。
- 提供编辑器、Git 属性、忽略规则和安全环境变量示例。
- 提供 Issue 与 Pull Request 模板。

## 当前尚未实现

- Vue 3 / Vite 前端项目及页面。
- FastAPI 后端项目、API 和业务服务。
- 数据库模型、迁移、PostgreSQL 或 Redis 连接。
- 商品、订单、库存、物流和消息能力。
- 市场数据、智能选品、评论分析和产品改良。
- 多语言内容生成、商品草稿和模拟上下架。
- 多语言智能客服、RAG 知识库、AI 任务编排和 MCP 工具调用。
- `MockShopeeAdapter`、`RealShopeeAdapterStub` 及真实平台连接。
- 测试框架、部署配置、容器编排和 CI/CD。

## 分支

- `main`：稳定发布分支。
- `develop`：日常集成开发分支。

功能与修复分支的完整约定见 `docs/git-workflow.md`。

## 安全

禁止提交 `.env`、API Key、Token、数据库密码、真实用户数据或真实店铺数据。配置示例只能包含安全占位符，日志、截图和演示数据必须脱敏。
