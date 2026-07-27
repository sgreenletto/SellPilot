# 公共后端底座测试

## 范围

测试覆盖 Settings、统一响应、异常与 Request ID、健康检查、Argon2、JWT、认证接口、平台适配器、工具注册器、LangGraph、任务/确认状态机、MCP 工具清单和 Alembic 可逆迁移。

测试不访问外网、真实 Shopee、真实 LLM、真实生产数据库或本机 PostgreSQL。

## 执行

在 `backend` 目录：

```powershell
uv sync
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
```

如需生成覆盖率报告：

```powershell
uv run pytest --cov=sellpilot --cov-report=term-missing
```

## 数据库策略

常规测试使用逐测试隔离的 `sqlite+aiosqlite` 数据库。Alembic 集成测试在临时 SQLite 文件上依次执行：

1. `upgrade head`
2. `downgrade base`
3. `upgrade head`

SQLite 只用于测试速度与隔离性；PostgreSQL 是目标数据库。PostgreSQL 专属行为和部署兼容性必须在后续受控环境验证。
