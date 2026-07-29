# Assistant Workflow Integration API

所有接口位于 `/api/v1/assistant`，要求 Bearer JWT，并使用统一 `ApiResponse<T>`。

## 生成计划

`POST /plan`

```json
{
  "message": "查询订单 ORD000001 的物流"
}
```

该接口语义不变：只返回意图、参数、缺失字段、Capability、Workflow 引用、步骤和风险；
不创建 Task，不执行 Tool。

## 创建或运行 Assistant Task

`POST /tasks`

```json
{
  "message": "查询订单 ORD000001 的物流",
  "execution_mode": "create_and_run"
}
```

`execution_mode`：

- `create_only`：创建 pending Task，不运行。
- `create_and_run`：创建后通过现有 `TaskRunner` 运行。

成功响应的 `data`：

```json
{
  "detected_intent": "logistics_query",
  "selected_capability": "logistics_query",
  "workflow_name": "logistics_query",
  "workflow_version": "1.0.0",
  "plan": {},
  "task_id": "00000000-0000-0000-0000-000000000000",
  "task_status": "succeeded",
  "execution_mode": "create_and_run",
  "confirmation_required": false,
  "confirmation_id": null,
  "duplicate": false,
  "created_at": "2026-07-29T10:00:00Z"
}
```

WRITE/HIGH_RISK Workflow 暂停确认时返回 HTTP 202；其他成功创建返回 HTTP 201。

幂等：

- 客户端可重用同一个合法 `X-Request-ID` 重放相同请求。
- 相同请求返回相同 `task_id`，`duplicate=true`，不会重复创建或执行。
- 相同 Request ID 配不同输入返回 HTTP 409 / `IDEMPOTENCY_CONFLICT`。

错误：

- 401：未认证。
- 409：`contract_only`、`unavailable`、状态冲突或幂等冲突。
- 422：缺失必要参数、unknown intent、工具名注入或 Workflow Schema 校验失败。
- 500：未处理的服务端错误；不会返回内部堆栈。

## 最近 Assistant Task

`GET /tasks?limit=5`

只返回当前用户通过 Assistant 创建的最近 Task，范围为 1–20。响应元素复用
`AgentTaskResponse`，不建立第二套 Task 返回格式。

Task 详情和审计链继续使用：

- `GET /tasks/{task_id}`
- `GET /tasks/{task_id}/steps`
- `GET /tool-calls?task_id={task_id}`
- `GET /confirmations?task_id={task_id}`
- `GET /tasks/{task_id}/operation-logs`
