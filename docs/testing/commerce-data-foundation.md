# 成员二数据基础测试

## 自动检查

```powershell
cd backend
uv run ruff format --check .
uv run ruff check .
uv run pytest -q tests/integration/test_commerce_import.py
uv run pytest -q tests/integration/test_migrations.py
```

## 覆盖范围

- 12 个 CSV 的完整 Schema 校验。
- 9,129 行模拟数据导入。
- 单个内部模拟店铺与六个站点源店铺标识保留。
- 13 张业务表的数量核对。
- 第二次导入插入 0 条、跳过 9,130 条。
- `is_mock_data=false` 时拒绝整个包且不产生部分写入。
- Alembic upgrade、downgrade、再次 upgrade 和 `alembic check`。

测试使用隔离 SQLite，不访问真实 Shopee、外网或本机 PostgreSQL。PostgreSQL 仍是目标数据库，合并里程碑前需要在受控 PostgreSQL 环境补充迁移与导入验证。
