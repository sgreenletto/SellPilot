# SellPilot Backend

SellPilot 公共后端架构底座，当前稳定版本为 **0.1.0**，属于 Foundation Milestone。该版本表示公共工程基线已建立，不代表完整业务已完成或已用于生产。

当前 `develop` 阶段在公共底座上增加成员三分析持久化与智能选品确定性计算内核，以及
成员二商品、SKU、库存、订单、物流、售后、评论、客服实验数据和类目趋势的持久化与导入
基础。选品 Service、API、Tool、工作流和页面，以及完整 Mock 平台操作、其他前端业务页面
和 AI/RAG 流程仍未实现。

v0.1.0 采用普通 Git Tag 标记，不创建 GitHub Release；当前不连接真实 Shopee。

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

导入前会使用 Pydantic Schema 校验 12 个 CSV；任一文件失败则事务回滚。重复执行按 `external_id` 跳过已有记录，不重复插入。当前数据包导入 9,129 行数据并创建一个内部模拟店铺，共形成 9,130 条数据库记录。

## 创建管理员

完成迁移后，通过交互式密码输入创建单用户管理员：

```powershell
uv run sellpilot-create-admin --username admin
```

密码由 `getpass` 读取，不作为命令行参数，也不会写入日志。重复用户名会明确失败。

## 启动 API

```powershell
uv run uvicorn sellpilot.main:app --host 127.0.0.1 --port 8000
```

基础地址为 `http://127.0.0.1:8000/api/v1`。

## MCP

MCP 服务使用官方 SDK 的 `FastMCP`，默认以 stdio 运行：

```powershell
uv run sellpilot-mcp
```

当前只暴露只读 `system_health`，不包含商品、订单、客服或外部 MCP 客户端。

## 智能选品 API

智能选品后端通过 `/api/v1/selection` 提供候选查询、确定性分析、任务详情、商品比较和 JSON 报告导出。数据来自数据库中的 Mock Shopee 商品与类目趋势，所有响应明确携带模拟数据标记。评分不依赖 LLM；当前解释使用经过结构化校验的规则模板，不宣称已接入真实模型。详细边界见 `../docs/architecture/selection-api-tools.md`。

## 测试与代码质量

```powershell
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
```

测试使用逐测试隔离的 SQLite 异步数据库，不访问本机 PostgreSQL、外网、真实 Shopee 或真实 LLM。SQLite 用于快速验证公共逻辑和迁移可逆性；PostgreSQL 仍是目标运行数据库，上线前必须在受控 PostgreSQL 环境补充兼容性验证。

## 平台边界

- `MockShopeeAdapter` 已提供数据库驱动的商品、订单、物流和消息只读能力；商品上下架、SKU 改价和库存调整只可通过内部待确认任务执行。
- `RealShopeeAdapterStub` 不发起网络请求、不读取真实密钥、不静默回退至 mock，且所有业务方法明确返回未配置错误。
- 业务表和导入数据不等同于适配器业务方法已经实现；上层代码仍不得直接依赖 CSV 或 `MockShopeeAdapter` 具体类。
