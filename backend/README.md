# SellPilot Backend

SellPilot 公共后端架构底座，当前稳定版本为 **0.1.0**，属于 Foundation Milestone。该版本表示公共工程基线已建立，不代表完整业务已完成或已用于生产。

本阶段在公共底座上增加成员三分析与内容持久化模型、Repository、Alembic 迁移，以及
智能选品确定性计算内核。选品 Service、API、Tool、工作流和页面，以及评论分析、
产品改良、内容生成、模型网关、商品、订单、库存、物流、客服和 RAG 仍未实现。

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

## 测试与代码质量

```powershell
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
```

测试使用逐测试隔离的 SQLite 异步数据库，不访问本机 PostgreSQL、外网、真实 Shopee 或真实 LLM。SQLite 用于快速验证公共逻辑和迁移可逆性；PostgreSQL 仍是目标运行数据库，上线前必须在受控 PostgreSQL 环境补充兼容性验证。

## 平台边界

- `MockShopeeAdapter` 的 ping 与公共契约状态可用；所有业务方法明确抛出未实现异常。
- `RealShopeeAdapterStub` 不发起网络请求、不读取真实密钥、不静默回退至 mock，且所有业务方法明确返回未配置错误。
