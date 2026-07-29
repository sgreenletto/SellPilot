# AI 管理测试

AI 管理回归覆盖：

- 运行状态和调用审计不泄露 API Key。
- 固定成员三评估集通过真实评估器运行，不读取手写通过率。
- Prompt 新版本请求只创建待确认任务，确认前版本数量不变。
- 确认后创建递增的不可变版本，并保留历史版本。
- 模板启用、停用和归档必须经过待确认流程。
- Prompt Schema 需要 `type=object`，敏感配置不得进入持久化快照。
- 首版不提供独立 AI 管理页面；Prompt、模型调用和评估通过 API、CLI 与测试报告验证。

后端针对性命令：

```powershell
cd backend
uv run pytest -q tests/integration/test_ai_management_api.py
```

2026-07-29 删除非核心 AI 管理页面后，需要重新运行前端全量检查。成员三固定 AI
评估集最近一次失败数为 0。
