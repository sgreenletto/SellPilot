# 成员三分析持久化测试

## 范围

本阶段测试验证成员三分析与内容持久化基础，不验证尚未实现的选品算法、评论分析模型、内容生成、API 或前端页面。

自动化测试覆盖：

- Alembic `upgrade head → downgrade base → upgrade head`。
- Alembic 元数据差异检查。
- 12 张成员三表均由迁移创建。
- 选品运行的状态筛选、分页和结果排名。
- 同一选品任务内来源商品和排名唯一约束。
- 选品总分和数据完整度范围约束。
- 评论证据的类型筛选、分页和来源评论追踪。
- 评论评分、评论置信度和改良频率范围约束。
- 产品改良报告与建议的证据链。
- 父记录存在结果或证据时禁止物理删除。
- Prompt 模板、版本、变更说明和最新版本查询。
- 模型调用成本、超时和重试约束。
- 商品内容工作对象范围唯一、内容版本事实快照和生成报告版本唯一约束。
- Prompt、内容、建议和报告的默认状态。

## 测试数据

测试只使用合成 ID 和内容，例如：

- `PROD0001`
- `REV000001`
- `TREND0000001`
- `fake-structured-model`

测试不访问成员二 CSV、外网、真实 Shopee、真实 LLM、真实用户或生产数据库。来源对象只通过稳定业务 ID 表达，避免让持久化测试绑定 CSV 列读取逻辑。

## 执行

在 `backend` 目录运行针对性测试：

```powershell
uv run pytest -q tests/integration/test_analysis_persistence.py tests/integration/test_migrations.py
```

运行完整后端质量检查：

```powershell
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

## PostgreSQL 验证

SQLite 自动化测试用于快速验证迁移可逆性、约束和 Repository 行为。PostgreSQL 是目标数据库，最终部署前还需在受控 PostgreSQL 环境验证：

- JSONB 字段与查询计划。
- `NUMERIC` 精度和返回类型。
- 外键 `RESTRICT` 行为。
- 组合索引在演示数据量及扩展数据量下的查询计划。
- 完整迁移链的 upgrade、downgrade 和重新 upgrade。
