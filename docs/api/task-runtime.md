# Task Runtime API

All endpoints use `/api/v1`, require `Authorization: Bearer <token>`, and return the
shared `code/message/data/request_id` envelope. `X-Request-ID` is generated or accepted
by the existing middleware and matches the body.

## Endpoints

| Method | Path | Success | Purpose |
|---|---|---:|---|
| GET | `/tasks/workflows` | 200 | Safe enabled workflow metadata |
| POST | `/tasks` | 201 | Create a validated pending task |
| GET | `/tasks` | 200 | Current user's paginated tasks |
| GET | `/tasks/{task_id}` | 200 | Safe task detail |
| GET | `/tasks/{task_id}/steps` | 200 | Ordered safe step history |
| POST | `/tasks/{task_id}/run` | 200/202 | Run a pending task |
| POST | `/tasks/{task_id}/resume` | 200/202 | Resume after confirmation |
| POST | `/tasks/{task_id}/retry` | 200/202 | Retry the failed current step |
| POST | `/tasks/{task_id}/rerun` | 201 | Create a new linked task |
| POST | `/tasks/{task_id}/cancel` | 200 | Cancel future execution |

`GET /tasks` supports `page`, `page_size`, `status`, `workflow_name`, `task_type`,
`created_from`, and `created_to`. Pagination retains `items/page/page_size/total/pages`.
Only the authenticated user's tasks are visible.

## Create and run

```json
{
  "workflow_name": "diagnostic",
  "workflow_input": {"message": "runtime check"}
}
```

Creation validates the workflow and its Pydantic input schema but does not execute it.
Clients then call:

```http
POST /api/v1/tasks/{task_id}/run
```

Successful deterministic execution returns 200. A tool that requires Confirmation
returns 202:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task_id": "uuid",
    "status": "waiting_confirmation",
    "confirmation_required": true,
    "confirmation_id": "uuid",
    "request_id": "uuid"
  },
  "request_id": "uuid"
}
```

The handler has not executed at this point. The client confirms through the existing
`POST /confirmations/{confirmation_id}/confirm`, then explicitly calls
`POST /tasks/{task_id}/resume`. Resume reads the successful linked ToolCall; it does
not execute the tool again.

## Workflow examples

`system_health_check` accepts `{}` and invokes the READ `system_health` tool. `selection`
uses the existing `SelectionAnalysisRequest` fields, for example:

```json
{
  "workflow_name": "selection",
  "workflow_input": {
    "site": "sg",
    "category_id": "CAT-001",
    "platform_fee_rate": "0.10"
  }
}
```

Selection results are based only on persisted synthetic Mock commerce data and remain
explicitly marked as Mock. No real Shopee or LLM call is made.

`review_analysis` accepts the existing `ReviewAnalysisCreateRequest` fields and runs
the registered `analyze_product_reviews` tool. It reuses the workflow AgentTask while
the original `/review-analysis` API remains compatible.

## Errors

Stable workflow/task codes include `WORKFLOW_NOT_FOUND`, `WORKFLOW_DISABLED`,
`WORKFLOW_VERSION_CONFLICT`, `TASK_NOT_RUNNABLE`, `TASK_ALREADY_RUNNING`,
`TASK_NOT_RESUMABLE`, `TASK_CONFIRMATION_PENDING`, `TASK_CONFIRMATION_INVALID`,
`TASK_RETRY_NOT_ALLOWED`, `TASK_ATTEMPT_EXHAUSTED`, `TASK_CANCEL_NOT_ALLOWED`,
`TASK_NODE_TIMEOUT`, `TASK_STATE_TOO_LARGE`, and `TASK_EXECUTION_CONFLICT`.

- 401: missing/invalid authentication
- 404: workflow/task not found or not owned
- 409: invalid state, execution race, pending/invalid confirmation, or exhausted retry
- 422: request/workflow input validation or state-size violation
- 202: valid confirmation pause, not an error

Task detail never returns trusted workflow input, serialized state, execution token,
runner identity, stack traces, or unredacted payloads.
