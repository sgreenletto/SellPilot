# Tool Execution Runtime Testing

## Coverage

The runtime suite covers definition validation, duplicate/version handling,
stable registry ordering, enabled and MCP filters, strict input/output models,
Pydantic serialization, read execution, synchronous compatibility, timeout,
bounded transient retry, safe errors, ToolCall/OperationLog persistence,
recursive redaction and truncation. A synchronous timeout regression waits for
the short test worker to finish and verifies that the late return cannot replace
the `timed_out` trace or add a success audit.

Write and high-risk tests verify that the initial handler is not called,
confirmation is linked, snapshots and warnings are enforced, idempotent
requests reuse one confirmation, conflicting payloads fail, confirmed execution
runs once, repeated/canceled confirmation does not run, and version drift fails
safely. API tests verify authentication, metadata safety, `200`/`202`, common
envelopes, request IDs and ToolCall pagination. MCP tests prove
`system_health` creates a caller-type `mcp` ToolCall.

Migration tests insert representative pre-runtime rows at `0002`, perform
`0001 -> 0002 -> 0003 (Commerce) -> 0004 (Tool Runtime)`, downgrade from
`0004` to `0003`, upgrade again, then downgrade to base, upgrade to head and
run `alembic check` on the disposable PostgreSQL test database.

## Commands

From `backend`:

```powershell
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run python -m pytest -q
uv run python -m pytest tests/unit/test_tool_execution.py -q
uv run python -m pytest tests/integration/test_tool_api.py -q
uv run python -m pytest tests/integration/test_tool_concurrency.py -q
uv run python -m pytest tests/integration/test_migrations.py -q
uv run python -m pytest tests/integration/test_mcp.py -q
```

From `frontend`:

```powershell
npm run format:check
npm run lint
npm run typecheck
npm run test:run
npm run build
```

## Concurrency boundary

PostgreSQL verifies the unique idempotency constraint and conditional confirmation
claim using simultaneous operations in independent sessions. A simulated hard
interruption after the durable claim verifies that the row remains `executing`,
has `execution_started_at`, retains a running ToolCall and is discoverable by
the stale-execution query. Before deployment, run simultaneous same-key create and
same-confirmation execute tests under production isolation and inspect that one
confirmation and one handler execution remain.
occurred.

All fixtures use synthetic users, isolated databases and test-local registries.
Test timeout/retry/write tools are never registered in the production registry.
