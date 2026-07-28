# 产品改良报告与确认草稿闭环

评论分析结果和证据进入确定性规则服务，生成带频率、严重度、优先级、置信度和评论 ID 的结构化建议。
频率来自持久化证据计数，置信度同时受证据质量和样本量约束；当前不调用真实 LLM。

```text
ReviewAnalysisResult / Evidence
→ ProductImprovementService
→ ProductImprovementReport / Suggestion
→ 人工编辑、采纳或忽略
→ ConfirmationTask(PENDING)
→ 用户明确确认
→ ProductContent / ProductContentVersion(DRAFT)
```

创建草稿请求只创建内部 AgentTask 和待确认任务。确认执行器才写商品内容草稿；不发布商品、不改价格或库存，
重复确认由公共确认状态机保证不会重复执行。报告导出返回结构化 JSON，由浏览器下载，服务器不写本地文件。

首版保持单用户、单 Mock Shopee 店铺边界。工厂建议仅是依据模拟评论的运营建议，实施前必须人工核对商品事实、
成本和工厂可行性。
