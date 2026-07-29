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

## 前端对话工作台

`/assistant` 使用中文优先的聊天式工作台，页面主标题由全局 `AppTopbar` 唯一提供。
用户发送消息后，前端仍先调用 `/assistant/plan` 判断意图、参数和能力状态；默认模式仅在
能力为 `available` 且参数完整时继续调用 Assistant Task 的 `create_and_run`。

前端同时保留两个次级模式：

- `create_only`：生成计划并创建 Task，但不运行；
- `plan_only`：只调用 `/assistant/plan`，不创建 Task、不调用 Tool。

任务执行结果不由前端推测。页面通过现有 Task 详情接口读取真实 `result`，对仍在
`pending` 或 `running` 的任务进行有界轮询，并在页面销毁时取消轮询计时器。订单、物流、
低库存、补货、选品、评论分析和产品改良结果按现有结构化输出展示；未知结构只展示公开
Task 响应中的基础字段。

内部 intent、Capability、Workflow、Step、Tool 和 Task ID 保持英文稳定标识，仅在默认
折叠的“查看执行计划”区域中显示。用户默认看到的是集中展示映射提供的中文名称、状态、
参数和步骤说明。常用任务面板只显示服务端 Capability Registry 返回的能力名称，点击只
填充示例文本，不会自动执行。
