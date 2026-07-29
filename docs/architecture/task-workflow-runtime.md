# Task Workflow Runtime

## Scope

TaskWorkflowRuntime is the single application-layer path for persistent workflow
execution. It extends the existing `AgentTask`, `AgentTaskStep`, `ToolExecutor`,
`ConfirmationService`, and `OperationLog`; it does not introduce a second task or
confirmation system.

```text
API / future AI assistant / compatible workflow
  -> TaskService
  -> WorkflowRegistry
  -> TaskRunner (atomic execution claim)
  -> AgentTaskStep
  -> action node or ToolExecutor
  -> READ: continue
  -> WRITE/HIGH_RISK: persist confirmation and pause
  -> existing Confirmation API and ToolExecutor recovery
  -> explicit TaskRunner.resume()
```

## Contracts

`WorkflowDefinition` declares a stable snake-case name and semantic version, typed
Pydantic input/output schemas, a finite node graph, entry node, bounded steps and
bounded task attempts. `NodeDefinition` supports `action`, `tool`, `branch`, `loop`,
`wait`, and `finish`; branch exits must be declared and every loop has a finite
`loop_limit`. Definitions contain server-side handlers only and never come from API
payloads.

`WorkflowRegistry` validates and stores definitions, rejects duplicate names, checks
versions, filters disabled workflows, and returns stable ordered metadata. It never
executes nodes. Tests use isolated registry instances.

`TaskExecutionContext` contains trusted task/user/request/workflow identity, validated
input, serializable state, current node and step, and bounded metadata. It deliberately
does not expose a database session. `NodeExecutionResult` contains safe output/state
updates, a declared next node, optional tool input, confirmation information, and a
safe retry decision.

## Persistence and execution ownership

`AgentTask` stores workflow name/version, validated input, parent rerun reference,
current node, serialized state, attempts, request ID, execution token, runner ID,
heartbeat, and lease expiry. `AgentTaskStep` stores stable sequence, node type,
attempt count, safe input/output summaries, error, ToolCall ID, Confirmation ID, and
timestamps.

Run, resume, and retry acquire ownership with one conditional database update. Only
the expected status and a null execution token can win. The winner commits the claim
before executing nodes. A cancellation clears the token; the runner refreshes the task
after node execution so a late result cannot overwrite cancellation. `heartbeat_at`
and `lease_expires_at` identify stale running work. This release provides stale
detection, not automatic takeover; recovery policy belongs to a later supervised job.

PostgreSQL tests verify conditional-update uniqueness. Production deployment still
requires real concurrent-load validation.

## Status rules

Task:

- `pending -> running | cancelled`
- `running -> waiting_confirmation | succeeded | failed | cancelled`
- `waiting_confirmation -> running | failed | cancelled`
- `succeeded`, `failed`, and `cancelled` are terminal for ordinary execution
- explicit `retry` is the only controlled reuse of a failed task; `rerun` always
  creates a new task linked by `parent_task_id`

Step:

- `pending -> running | skipped | cancelled`
- `running -> waiting_confirmation | succeeded | failed | cancelled`
- `waiting_confirmation -> running | succeeded | failed | cancelled`
- explicit retry changes only the current retryable failed step back to running and
  increments `attempt_count`

## Tool and confirmation integration

Tool nodes never call a `ToolDefinition.handler`. `TaskRunner` builds a
`ToolExecutionContext` with task and step IDs and invokes the existing `ToolExecutor`.
READ results create a linked ToolCall and continue.

WRITE and HIGH_RISK tools create/reuse the existing Confirmation. The step and task
enter `waiting_confirmation`, keep ToolCall/Confirmation IDs, release execution
ownership, and stop. After the existing Confirmation API succeeds, the client calls
`POST /tasks/{id}/resume`. Resume checks ownership, task/step/confirmation states,
and that the successful ToolCall belongs to the same task and step. It reuses the
persisted ToolCall output and never invokes the handler again.

Cancellation of a waiting task cancels a still-pending Confirmation. Confirmed,
executing, or completed external effects are never described as rolled back.

Async node timeouts cancel the awaiting coroutine. A synchronous node is isolated with
`asyncio.to_thread`; its worker thread may continue after the API records a timeout,
but it has no database session and its late result is discarded. Services called by
write tools remain responsible for transaction boundaries; TaskRunner never claims
that a timeout rolled back external work.

## Retry, resume, rerun, and cancel

| Operation | Meaning | Identity |
|---|---|---|
| retry | Retry the current retryable failed step within declared limits | Same task and step |
| resume | Continue after a successful trusted Confirmation | Same task and step |
| rerun | Start the original validated input again | New task with `parent_task_id` |
| cancel | Stop future workflow progress | Same task; completed effects remain |

## Audit and data safety

OperationLog records `task_created`, `task_started`, step success/failure,
confirmation waiting/resume, retry, rerun, cancellation, and task success/failure.
Task events reference task, step, ToolCall, and Confirmation where applicable.
ToolCall remains the technical tool trace; OperationLog is the business task history.

Task Center reads those records through the existing repositories and runtimes. It
does not add a second Task, Step, Runner, registry, executor, Confirmation, log, or API
envelope. `TaskCenterService` is the application-layer policy for
`available_actions`; routes only validate protocol inputs and delegate. List queries
remain constant-query and detail collections are separate, on-demand endpoints.

Confirmation and ToolCall reads are scoped to the authenticated owner. ToolExecutor
validates Task existence, Task ownership, Step existence, and Task/Step consistency
before it creates ToolCall, Confirmation, or OperationLog records. Confirmation
cancel/failure synchronizes a still-waiting Task in the service transaction, while
success deliberately requires an explicit TaskRunner resume. Public runtime schemas
redact sensitive keys recursively, limit depth/list/string/byte size, and never expose
serialized state, execution ownership fields, raw tool payloads, or tracebacks.

Workflow input and state reject secret-bearing fields. Step summaries and audit details
reuse the tool runtime's recursive redact-then-truncate logic. State has a hard byte
limit and is never returned by the API. Stack traces and raw internal exceptions are
not persisted or returned.

## Production definitions and boundaries

- `diagnostic`: deterministic runtime/step verification; no LLM.
- `system_health_check`: invokes the registered READ `system_health` tool through
  ToolExecutor.
- `selection`: adapts the existing `score_product_opportunity` tool and Selection
  Service. The scoring formula and legacy Selection API are unchanged.
- `review_analysis`: adapts the registered READ `analyze_product_reviews` tool,
  reuses the current AgentTask, and preserves the existing Review Analysis API,
  domain core and evidence persistence.
- `product_improvement`: adapts the registered READ
  `generate_product_improvement_plan` tool. Creating a product-content draft remains
  a separate HIGH_RISK Confirmation operation and never runs during report generation.
- `inventory_replenishment`: adapts the registered READ
  `analyze_inventory_replenishment` tool and returns deterministic SKU replenishment
  evidence without changing inventory.

LangGraph remains available for the existing bounded explanation graph. It is not a
second persistence runtime. A future graph adapter must still delegate task state,
tools, confirmation, and audit to TaskRunner.

## Member integration template

1. Define strict Pydantic input/output schemas.
2. Put deterministic business behavior in a Service.
3. Register tools in the existing ToolRegistry and execute them via ToolExecutor.
4. Define finite nodes and routes; set loop, step, timeout, and attempt limits.
5. Keep node handlers free of sessions, SQL, adapters, and direct tool handlers.
6. Assign READ/WRITE/HIGH_RISK accurately; writes must supply idempotency and required
   snapshots.
7. Register one WorkflowDefinition in the production registry.
8. Add Task, Step, ToolCall, confirmation, concurrency, and API tests.
