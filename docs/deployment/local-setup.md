# 本地 Demo 环境

## 要求

- Windows PowerShell 5.1+；
- Python 3.12 与 uv；
- Node.js 22+ 与 npm；
- PostgreSQL 17；
- 可选 Docker Desktop。

## 配置

```powershell
Copy-Item .env.example .env
```

只编辑根目录 `.env`。数据库保持 PostgreSQL，`PLATFORM_ADAPTER=mock`。不要在
`backend` 创建第二份 `.env`，不要把密码、JWT 或模型密钥提交 Git。

## 初始化

```powershell
uv sync --project .\backend
npm ci --prefix .\frontend
.\scripts\init-demo.ps1 -AdminUsername admin
```

需要 Mock 政策 smoke 时加 `-IncludeKnowledge`；真实知识数据按
`knowledge-base-initialization.md` 单独导入并验收。

## 启动与检查

```powershell
.\start-sellpilot.bat --check
.\start-sellpilot.bat
.\scripts\check-demo-readiness.ps1
```

启动器复用已有健康 SellPilot 后端。未知进程占用端口时只报告 PID/进程名，不自动
终止。Demo 模式不使用 reload；开发者单独运行后端时才按需开启开发重载。

## 质量门禁

```powershell
cd backend
uv run ruff format --check .
uv run ruff check .
uv run alembic heads
uv run alembic upgrade head
uv run alembic current
uv run alembic check
uv run pytest -q

cd ..\frontend
npm run format:check
npm run lint
npm run typecheck
npm run test:run
npm run build
```

Docker 环境见 `docker-compose.md`。
