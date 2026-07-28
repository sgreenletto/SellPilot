# 评论分析 Service、API、Tool 与工作流测试

覆盖评论筛选与分页、多批读取和数量上限、任务创建与运行、三个 AgentTaskStep、空数据失败、失败状态持久化、幂等复用与冲突、有限重试、证据分页、所有权、未登录、Schema 错误、资源不存在，以及两个 Tool 的统一执行记录。

```powershell
cd backend
uv run pytest tests/unit/test_review_analysis_workflow.py -q
uv run pytest tests/integration/test_review_analysis_service.py -q
uv run pytest tests/integration/test_review_analysis_api.py -q
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
```

测试只使用隔离 SQLite 和合成/Mock 数据，不访问真实平台、模型、翻译服务或生产数据库。
