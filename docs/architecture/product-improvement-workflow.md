# 产品改良报告与确认草稿闭环

评论分析结果先由确定性证据规则限定可改良类别：只有低评分或含明确缺点表达的评论才能进入
产品改良。启用 `aliyun_bailian` 时，百炼模型根据这些限定类别及原文生成标题和可执行方案；
模型输出必须通过结构化 Schema 校验，且类别集合必须与输入完全一致，不能新增“描述不符”等
无证据问题。未配置模型时才使用离线规则文案。没有改进信号时返回空报告，不凭空生成问题。
频率、严重度和优先级仍由持久化证据确定，LLM 不参与证据计数或类别判定。
置信度与原始评论 ID 保留在结构化结果中用于审计，不作为前端或 Markdown 报告的主要决策指标。
报告算法版本升级后不会复用旧算法报告，而是为同一分析生成递增的新版本。

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
重复确认由公共确认状态机保证不会重复执行。内部报告与接口保持结构化 Schema，面向用户的下载格式为
Markdown，由浏览器下载，服务器不写本地文件。

首版保持单用户、单 Mock Shopee 店铺边界。工厂建议仅是依据模拟评论的运营建议，实施前必须人工核对商品事实、
成本和工厂可行性。
