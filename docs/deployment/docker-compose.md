# Docker Compose 本地演示环境

Compose 环境包含 PostgreSQL 17、SellPilot backend 和静态 frontend。当前代码不依赖 Redis
或 pgvector，因此编排不会为了形式引入未使用的服务。所有平台操作默认使用
`PLATFORM_ADAPTER=mock`。

## 配置边界

Compose 使用 `COMPOSE_*` 变量，避免自动把根目录 `.env` 中的应用密钥展开进
`docker compose config`。默认密码只适合单机 Demo，任何共享环境都必须在当前终端设置：

```powershell
$env:COMPOSE_DB_PASSWORD = Read-Host "PostgreSQL password"
$env:COMPOSE_JWT_SECRET_KEY = Read-Host "JWT secret"
```

不要把这些值写入仓库文件，也不要把 `docker compose config` 的完整输出粘贴到公开日志。

## 验证和启动

```powershell
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

backend 容器会等待 PostgreSQL 健康，随后执行 `alembic upgrade head` 并启动无 reload 的
API。访问：

- 前端：`http://127.0.0.1:5173`
- API live：`http://127.0.0.1:8000/api/v1/health/live`
- API ready：`http://127.0.0.1:8000/api/v1/health/ready`

首次初始化数据：

```powershell
docker compose exec backend uv run --no-sync sellpilot-create-admin --username admin
docker compose exec backend uv run --no-sync sellpilot-import-mock-data
docker compose exec backend uv run --no-sync sellpilot-import-knowledge
docker compose exec backend uv run --no-sync sellpilot-check-demo-readiness
```

管理员密码通过隐藏提示输入。知识数据未导入时应标记 `BLOCKED_RAG_DATA`，不能宣称 RAG
真实命中通过。

## 停止与重置

普通停止会保留 PostgreSQL volume：

```powershell
docker compose down
```

仅在明确确认不再需要容器数据库数据时，才由用户手动执行：

```powershell
docker compose down --volumes
```

该操作会删除 Compose 专用数据库 volume，禁止对本机现有 PostgreSQL 数据库使用等价清空操作。
