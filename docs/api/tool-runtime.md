# Tool Runtime API

All routes use `/api/v1`, require `Authorization: Bearer <token>`, accept and
return JSON, and use the common `code/message/data/request_id` envelope.
`X-Request-ID` follows the common contract.

## Endpoints

| Method and path | Purpose | Success |
| --- | --- | --- |
| `GET /tools` | Safe registered tool metadata, including enabled state | `200` |
| `GET /tools/{tool_name}` | Safe metadata for one tool | `200` |
| `POST /tools/{tool_name}/execute` | Execute through the unified runtime | `200` for read, `202` when confirmation is required |
| `GET /tool-calls` | Paginated safe execution traces | `200` |
| `GET /tool-calls/{tool_call_id}` | One safe execution trace | `200` |

Tool metadata contains `name`, `version`, `description`, `risk_level`,
`timeout_seconds`, `enabled`, `expose_to_mcp`, `confirmation_required`,
`input_json_schema` and `output_json_schema`. It excludes handlers, Python
module paths, secrets and internal exception configuration.

## Execution

```json
{
  "input": {},
  "task_id": null,
  "task_step_id": null,
  "idempotency_key": null,
  "target_type": "tool",
  "target_id": null,
  "before_snapshot": null,
  "after_snapshot": null,
  "risk_warning": null
}
```

`system_health` is read-only, accepts an empty object and returns `200`:

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "tool_call_id": "00000000-0000-0000-0000-000000000000",
    "tool_name": "system_health",
    "tool_version": "1.0.0",
    "status": "succeeded",
    "data": {
      "app_name": "SellPilot",
      "app_version": "1.0.0",
      "environment": "development",
      "adapter": "mock",
      "status": "ok"
    },
    "error_code": null,
    "error_message": null,
    "confirmation_required": false,
    "confirmation_id": null,
    "attempt_count": 1,
    "duration_ms": 0,
    "request_id": "00000000-0000-0000-0000-000000000000",
    "task_id": null,
    "started_at": "2026-07-28T00:00:00Z",
    "completed_at": "2026-07-28T00:00:00Z"
  },
  "request_id": "00000000-0000-0000-0000-000000000000"
}
```

A write or high-risk call requires authenticated `task_id` and a real
`idempotency_key`. The first call returns `202`, status
`waiting_confirmation`, `confirmation_required=true` and `confirmation_id`.
The handler has not run. High-risk calls additionally require both snapshots
and a non-empty risk warning. Confirmation is performed by the existing
`POST /confirmations/{confirmation_id}/confirm` route.

## ToolCall queries

The list uses common `page`/`page_size` pagination and returns `pages`.
Optional filters are `tool_name`, `status`, `risk_level`, `task_id`,
`created_from` and `created_to`. Returned summaries are already recursively
redacted and bounded. Raw credentials, stack traces and unredacted payloads are
never returned.

## Errors

| Code | Typical HTTP status |
| --- | --- |
| `UNAUTHENTICATED` | `401` |
| `TOOL_NOT_FOUND` | `404` |
| `TOOL_DISABLED`, `TOOL_VERSION_CONFLICT` | `409` |
| `TOOL_NOT_EXPOSED` | `403` |
| `TOOL_INPUT_INVALID`, `TOOL_OUTPUT_INVALID` | `422` / `502` |
| `TOOL_CONFIRMATION_REQUIRED` | represented by successful `202` data |
| `TOOL_CONFIRMATION_INVALID`, `TOOL_IDEMPOTENCY_CONFLICT` | `409` |
| `TOOL_TIMEOUT` | `504` |
| `TOOL_RETRY_EXHAUSTED` | `503` |
| `TOOL_EXECUTION_FAILED` | `500` with a safe message |

Every response retains its request ID. Validation and runtime errors do not echo
raw input, Python stacks, SQL, file paths or credentials.

## Mock boundary

The current production registry contains only system diagnostics. ToolCall and
OperationLog records mark the configured Mock mode. No API route performs a
real Shopee operation, and `RealShopeeAdapterStub` is not treated as success.
