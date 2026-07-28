# 评论分析 API

评论分析 API 位于 `/api/v1/review-analysis`，所有端点均要求 Bearer JWT。当前只读取正式导入的 Mock Shopee 评论并持久化规则分析结果，不访问真实 Shopee，不调用真实模型或翻译服务。

## 端点

- `GET /reviews`：按商品、站点、语言、评分、时间和 offset/limit 查询评论。
- `POST /analyses`：创建 `PENDING` 分析任务，返回 202。
- `POST /analyses/{analysis_id}/run`：运行待处理任务。
- `GET /analyses/{analysis_id}`：查询进度、当前步骤、步骤列表、失败原因和结构化结果。
- `GET /analyses/{analysis_id}/evidence`：分页读取完整证据。

创建和执行分离，避免创建长任务时请求一直无反馈。调用方应展示 `PENDING`、`RUNNING`、`SUCCEEDED` 和 `FAILED`。

## 创建请求

```json
{
  "idempotency_key": "review-analysis-demo-001",
  "product_id": "PROD0001",
  "site": "sg",
  "languages": ["English", "Malay"],
  "min_rating": 1,
  "max_rating": 5,
  "batch_size": 100,
  "maximum_reviews": 1000,
  "max_attempts": 2
}
```

相同用户、商品和幂等键下，同摘要返回已有任务并标记 `duplicate=true`，不同摘要返回冲突。单批最多 100 条，单任务最多 5,000 条。

结果包含算法版本、`analysis_mode=rule`、明确为空的 Prompt/模型版本、数据质量、情感、主题、痛点、关键词、趋势和逐条判断。当前没有真实模型调用，不得伪造 Prompt 或模型版本。

## Tool

- `get_product_reviews`
- `analyze_product_reviews`

两者均经过统一 `ToolExecutor`，记录 ToolCall 输入/输出摘要、耗时、状态和安全错误，且不暴露给 MCP。
