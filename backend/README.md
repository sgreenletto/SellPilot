# SellPilot Backend

SellPilot 后端当前发布候选版本为 **0.5.0**，对应 AI 运营助手与跨模块工作流集成里程碑。

当前 `develop` 已包含 PostgreSQL 业务数据、Assistant Task Runtime、统一 Tool/Workflow 注册表、
智能选品、评论分析、产品改良、内容生成、知识库检索和客服回复建议。所有平台动作继续通过
适配器和确认边界执行；项目仍为单用户、单模拟店铺和 Mock Shopee 验证环境。

v0.5.0 发布说明见 [`docs/releases/v0.5.0.md`](../docs/releases/v0.5.0.md)；当前不连接真实 Shopee。

## 技术栈

- Python 3.12 与 uv
- FastAPI、Pydantic v2、pydantic-settings
- SQLAlchemy 2 异步模式、Alembic
- PostgreSQL 目标数据库
- PyJWT、pwdlib Argon2
- LangGraph 1.2.9
- 官方 Python MCP SDK 1.28.1
- pytest、pytest-asyncio、httpx、ruff

## 安装

在 `backend` 目录执行：

```powershell
uv sync
```

将根目录 `.env.example` 复制为根目录 `.env` 并只在本地填写安全配置。不得提交 `.env`。

## 数据库迁移

确保 `DATABASE_URL` 指向获准使用的 PostgreSQL 数据库，然后执行：

```powershell
uv run alembic upgrade head
```

回退全部基础迁移：

```powershell
uv run alembic downgrade base
```

应用启动不会执行 `create_all`。正式结构只通过 Alembic 管理。

成员三持久化结构包括选品运行与结果、评论分析与证据、产品改良报告、商品内容版本、Prompt 版本、模型调用和生成报告。该结构使用稳定来源业务 ID 对接后续商品与评论服务，不直接依赖模拟 CSV；详细设计见 `../docs/architecture/analysis-persistence.md`。

评论分析纯领域内核位于 `sellpilot.domain.review_analysis`，提供多语言质量检查、确定性情感与主题分类、证据聚合及站点/月度趋势。内核不读取数据库或 CSV，不调用真实模型；应用层通过 Service、API、统一 ToolExecutor 和 TaskWorkflowRuntime 接入。

评论分析应用层现提供有界评论查询、分阶段分析任务、证据分页、幂等控制、AgentTaskStep 工作流以及统一 ToolExecutor 工具，前端 Review Analysis Workbench 已接入这些 API。当前仍使用规则内核，Prompt 和模型版本明确为空；真实 Model Gateway 尚未实现。

成员二迁移 `20260728_0003` 创建 13 张业务表，详细设计见 `../docs/architecture/commerce-data-foundation.md`。

## 导入模拟业务数据

完成数据库迁移后执行：

```powershell
uv run sellpilot-import-mock-data
```

默认读取仓库的 `data/demo/shopee_mock/`。也可显式指定目录：

```powershell
uv run sellpilot-import-mock-data --data-dir ../data/demo/shopee_mock
```

导入前会使用 Pydantic Schema 校验 12 个 CSV；任一文件失败则事务回滚。重复执行按
`external_id` 跳过已有记录，不重复插入。当前数据包共校验 9,254 行记录，包含用于
Assistant 选品验证的 3 个明确标记为 Mock 的新加坡母婴候选商品。

## 创建管理员

完成迁移后，通过交互式密码输入创建单用户管理员：

```powershell
uv run sellpilot-create-admin --username admin
```

密码由 `getpass` 读取，不作为命令行参数，也不会写入日志。重复用户名会明确失败。

## 启动 API

```powershell
uv run sellpilot-start-api
```

命令从根目录环境配置读取 `API_HOST` 和 `API_PORT`，默认基础地址为
`http://127.0.0.1:8000/api/v1`。它会先检查健康接口；已有健康 SellPilot 实例时直接
复用，未知进程占用端口时明确报错且不会自动终止进程。需要显式热重载时使用
`uv run sellpilot-start-api --reload`。

## MCP

MCP 服务使用官方 SDK 的 `FastMCP`，默认以 stdio 运行：

```powershell
uv run sellpilot-mcp
```

当前只暴露只读 `system_health`，不包含商品、订单、客服或外部 MCP 客户端。

## 智能选品 API

智能选品后端通过 `/api/v1/selection` 提供候选查询、确定性分析、任务详情、商品比较和 JSON 报告导出。数据来自数据库中的 Mock Shopee 商品与类目趋势，所有响应明确携带模拟数据标记。评分不依赖 LLM；当前解释使用经过结构化校验的规则模板，不宣称已接入真实模型。详细边界见 `../docs/architecture/selection-api-tools.md`。

## Task Workflow Runtime

`/api/v1/tasks` 提供已认证的工作流任务创建、查询、步骤历史、run、resume、
retry、rerun 和 cancel。唯一 Workflow Registry 已注册订单、物流、库存、选品、评论、
产品改良、内容生成、知识检索和客服分支等工作流；所有工具节点统一经过 ToolExecutor。
WRITE/HIGH_RISK 会暂停到现有 Confirmation，确认成功后由显式 resume 继续。
详细边界见 `../docs/architecture/task-workflow-runtime.md`。

## 测试与代码质量

```powershell
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
```

测试使用独立的 PostgreSQL `sellpilot_test` 数据库，不访问开发数据库、外网、真实
Shopee 或真实 LLM。测试启动时自动创建测试数据库，并在用例之间重建表结构；迁移测试
在同一隔离数据库中验证真实 PostgreSQL 升降级。

## 平台边界

- `MockShopeeAdapter` 已提供数据库驱动的商品、订单、物流和消息只读能力；商品上下架、SKU 改价和库存调整只可通过内部待确认任务执行。
- `RealShopeeAdapterStub` 不发起网络请求、不读取真实密钥、不静默回退至 mock，且所有业务方法明确返回未配置错误。
- 业务表和导入数据不等同于适配器业务方法已经实现；上层代码仍不得直接依赖 CSV 或 `MockShopeeAdapter` 具体类。
