# 评论分析应用层、Tool 与工作流

```text
API / ToolExecutor
→ ReviewAnalysisService
→ PlatformAdapter.list_reviews
→ Step 5 review_analysis domain core
→ ReviewAnalysisRepository / TaskService
→ ReviewAnalysisResult / Evidence / AgentTask / AgentTaskStep
```

路由只做协议转换、身份注入和统一响应。评论读取经过平台适配器抽象；真实适配器仍是无网络 Stub。领域内核不读取数据库，持久化只由内部 Service 执行。

创建分析时内部 Service 创建 `AgentTask(REVIEW_ANALYSIS)`、`load_reviews`、`analyze_reviews`、`persist_results` 三个步骤及一个 `PENDING` 分析。运行时逐步保存输入/输出摘要。失败状态在抛出 API 错误前提交，避免请求回滚丢失诊断记录。

评论按最多 100 条一批读取，单任务默认最多 1,000、上限 5,000。语言、站点、评分和时间条件下推适配器，所有列表都有上限。

请求摘要排除幂等键后使用规范 JSON 和 SHA-256。查询条件为用户、商品和 JSON 幂等键；同键同摘要复用，同键不同摘要拒绝。

当前记录：

- `analyzer_version=review-analysis-v1.1.0`
- `analysis_mode=rule`
- `prompt_version=null`
- `model_version=null`

Step 10 接入 Model Gateway 后再关联 PromptVersion 与 ModelInvocation，不在当前阶段伪造调用记录。

AgentTask 输入只保存筛选摘要，不保存整批评论或幂等键；重试错误只保存异常类型。返回评论不含买家、订单等个人标识。评论分析不修改商品、库存、价格或平台状态，因此不触发平台写操作确认。
