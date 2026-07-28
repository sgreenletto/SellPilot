# Tool Execution Runtime

## Scope

SellPilot has one tool execution path for internal APIs, services, agents, workflows,
MCP and tests:

```text
caller
  -> ToolRegistry
  -> ToolExecutor
  -> input schema and risk gate
  -> handler or ConfirmationTask
  -> timeout and bounded retry
  -> output schema
  -> ToolCall technical trace
  -> OperationLog business audit
  -> ToolExecutionResult
```

This runtime does not implement product, order, review, RAG or customer-service
business behavior. Production registration currently contains only
`system_health`. Tools call Services; they do not query SQL or call
`MockShopeeAdapter` directly.

## Contracts and responsibilities

`ToolDefinition` is immutable and declares the stable snake-case name, semantic
version, description, Pydantic input and output models, `ToolRiskLevel`, timeout,
explicit `RetryPolicy`, idempotency, enabled/MCP flags, sensitive fields and the
handler. Public metadata contains JSON schemas but never the handler, module path,
secrets or internal configuration.

`ToolRegistry` validates and stores definitions. It rejects duplicate names,
invalid schemas, incompatible versions and timeout limits. Listing order is by
name. A test creates its own registry; it must not mutate the application
registry. Registry lookup never executes a handler.

`ToolExecutionContext` carries a validated UUID request ID, user/task/step and
idempotency references, caller type/name and small scalar metadata. It has no
`confirmed` boolean. A caller-provided `confirmation_id` is rejected; the trusted
confirmation executor obtains that ID from the database.

`ToolExecutor` owns validation, risk gating, execution, timeout, retry, result
validation, redaction and persistence. `ToolExecutionResult` is the one result
shape and includes the call ID, version, status, data or safe error, confirmation
reference, attempt count, duration, request/task IDs and timestamps.

## Risk rules

| Risk | Initial call | Confirmation | Retry |
| --- | --- | --- | --- |
| `read` | Executes immediately | Never created | Only explicitly listed transient codes, maximum three attempts |
| `write` | Handler is not called | Required, with task, user and idempotency key | One attempt |
| `high_risk` | Handler is not called | Required with before/after snapshots and risk warning | One attempt |

Confirmation stores the validated tool name, exact version, validated input,
digest and request ID. `ConfirmationService` atomically claims a pending or
confirmed row, records `execution_started_at` and durably commits the
`executing` state before calling the handler. Its registered `tool.execute`
executor reloads trusted data, verifies the database status and exact version,
validates the saved input again and executes once. Repeated confirmation returns
the executing or terminal row without another handler call. A canceled,
malformed or version-conflicting confirmation cannot execute.

The confirmation input cannot contain secret values. Such tools must persist a
server-side secret reference instead. This avoids placing credentials in the
confirmation table.

## Idempotency and concurrency

`write` and `high_risk` contexts require a dedicated idempotency key. The stored
unique scope binds key, user, tool/version and target; the separately stored
canonical validated input digest detects a changed payload in the same scope.
An exact duplicate reuses the active confirmation; a different invocation using
the same scoped key returns `TOOL_IDEMPOTENCY_CONFLICT`. The database unique
constraint prevents duplicate rows, including races. Confirmation claiming uses
a conditional database update, in addition to PostgreSQL transaction semantics,
so only one claim can progress.

SQLite tests use independent sessions to verify constraints, simultaneous
same-key creation and conditional confirmation claiming. SQLite does not model
PostgreSQL row-lock scheduling exactly. PostgreSQL remains the production target;
deployment verification must exercise simultaneous requests at the configured
isolation level.

An interruption after the durable claim leaves the confirmation as `executing`
with an execution start timestamp and its ToolCall as `running`. These rows are
not treated as success and user retries do not invoke the handler again.
`list_stale_executing` provides the bounded query needed by a future recovery
task. Recovery must reconcile the Service transaction and its business
idempotency guarantee before deciding whether to fail or retry the operation;
this milestone does not auto-retry stale writes.

## Timeout and retry

Async handlers run under `asyncio.wait_for`. Synchronous compatibility handlers
run in a worker thread so they do not block the event loop. A Python timeout
cannot prove that a synchronous thread has stopped or that an external write was
rolled back; write tools must use Service transactions. A late synchronous
return has no path back to persistence, so it cannot replace the terminal
`timed_out` ToolCall or append a success OperationLog. The worker may still
finish its own external side effect, which is why the runtime does not claim
automatic rollback.

Retries are bounded by `RetryPolicy`. The attempt count includes the first call.
Input/output validation, permission, confirmation, idempotency and other
non-transient failures are not retried. Every attempt is summarized in
`ToolCall.attempt_history`. Write and high-risk tools always have one attempt.

## Audit and redaction

`ToolCall` is the technical trace: caller, request/task/confirmation references,
safe input/output summaries, attempts, duration and safe error. `OperationLog`
is the concise business audit: action, target, risk, caller, linked IDs, result
and explicit Mock marker. It does not duplicate large payloads.

Redaction recursively copies Pydantic models, mappings, lists and tuples.
Case-insensitive default sensitive names include passwords, secrets, API keys,
access/refresh tokens, authorization, cookies, partner keys, JWTs and
credentials. A definition may add field names. Oversized summaries are replaced
with a `truncated` record, original byte size and bounded redacted preview.

## MCP

The MCP server lists only definitions that are enabled and
`expose_to_mcp=true`. High-risk exposure requires an explicit code-level opt-in.
Every MCP function is a thin bridge into `ToolExecutor` with caller type `mcp`;
it does not call a handler directly. MCP cannot bypass write confirmation.

## Member integration template

1. Define strict Pydantic input and output schemas.
2. Implement deterministic business behavior in a Service.
3. Write a small handler that calls that Service.
4. Create one `ToolDefinition` with a stable name and version.
5. Register it in the application registry.
6. Select `read`, `write` or `high_risk`.
7. Configure a bounded timeout and explicit retry policy.
8. Declare additional sensitive fields.
9. Add registry, execution, failure and audit tests.
10. For writes, provide target, snapshots where required and an idempotency key.
11. Never access SQL or `MockShopeeAdapter` from the tool.
12. Never call a handler outside `ToolExecutor`.
