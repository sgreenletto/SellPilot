# Assistant Workflow Integration

## 边界

Assistant 有两个独立入口：

- `POST /api/v1/assistant/plan`：只识别意图、提取参数并生成计划；不创建 Task，不执行 Tool。
- `POST /api/v1/assistant/tasks`：对计划再次校验后创建 Task，并按请求选择只创建或立即运行。

执行入口不接受 Tool 名称或 Workflow 名称。内部选择只能来自
`AssistantCapabilityRegistry` 引用的 `WorkflowDefinition`，Workflow 的业务调用只能经过
`TaskRunner` → `ToolExecutor`。

## 执行链

```text
AssistantTaskRequest
  -> AssistantPlanService
  -> AssistantCapabilityRegistry
  -> WorkflowRegistry
  -> TaskService.create_workflow_task
  -> AgentTask
  -> TaskRunner (create_and_run only)
  -> WorkflowDefinition
  -> ToolExecutor
  -> ToolCall / OperationLog
  -> ConfirmationTask (WRITE / HIGH_RISK only)
```

API 路由只负责请求/响应转换；Task 创建、幂等检查和运行编排位于
`AssistantTaskService`。

## 幂等与所有权

- `X-Request-ID` 是 Assistant Task 创建幂等键。
- 幂等范围为当前用户 + Request ID。
- PostgreSQL 使用事务级 advisory lock 串行化同一范围内的创建，再查询既有 Task。
- 同一 Request ID、同一安全摘要和同一 Workflow 输入返回原 Task；不同输入返回 409。
- 已成功或正在等待确认的 Task 不会因重放请求再次执行。
- Task、Step、ToolCall、Confirmation、OperationLog 继续使用现有用户所有权过滤。

## 安全摘要

`AgentTask.user_input` 只保存带 `source=assistant` 的截断、敏感模式脱敏摘要。
Workflow 参数经过其 Pydantic Schema 校验后写入现有 `workflow_input`。Intent、
Capability 和 Workflow 记录在 `task_created` OperationLog 的安全
`creation_context` 中。公开 Task 响应不返回原始输入、`workflow_input` 或
`serialized_state`。

## READ、WRITE 与确认

- READ Workflow 可由 `create_and_run` 直接执行，但仍创建 Step、ToolCall 和 OperationLog。
- WRITE/HIGH_RISK Tool 仍由 `ToolExecutor` 创建 `ConfirmationTask`；Assistant 不降低风险。
- Task 进入 `waiting_confirmation` 后，由现有 Confirmation API 确认或取消。
- 确认执行有幂等保护；成功后由现有 `POST /tasks/{id}/resume` 继续 Workflow。
- 取消确认会把 Task/Step 置为正确的 cancelled 终态。

## 已接入 Workflow

- `selection@1.0.0`
- `review_analysis@1.0.0`
- `product_improvement@1.0.0`
- `inventory_replenishment@1.0.0`
- `low_stock_check@1.0.0`
- `order_query@1.0.0`
- `logistics_query@1.0.0`

`order_query` 先执行 Branch 节点：有 `order_id` 走 `get_order`，否则走
`list_orders`。Branch 输出记录 `selected_branch`，最大 3 个 Step，没有循环或无限重试。

Content、RAG 和 Customer Service 尚未满足统一运行时条件，分别保持
`contract_only`、`contract_only`、`unavailable`。
