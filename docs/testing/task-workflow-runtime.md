# Task Workflow Runtime Testing

## Coverage

The suite covers typed definition validation, registry isolation, stable ordering,
diagnostic and system-health execution, Step sequence and persistence, linked
ToolCalls, task audit events, safe input rejection, retry-in-place, API ownership and
pagination, confirmation pause/confirm/resume, rerun/cancel, and Selection/Review
Analysis/Product Improvement adapter compatibility. The Product Improvement test
proves report generation uses the shared TaskRunner and ToolExecutor; draft creation
remains behind the shared HIGH_RISK Confirmation boundary.

Concurrency tests use separate SQLAlchemy sessions. A blocked test node lets one
request commit the execution claim before a second run/retry request attempts to
claim the same task. Only one request invokes the node. Existing Tool Runtime tests
continue to cover concurrent confirmation execution and idempotency.

Migration tests verify:

- one Alembic head and unique revision IDs;
- legacy task/step backfill;
- `0001 -> 0002 -> 0003 -> 0004 -> 0005`;
- task, step, confirmation, and audit columns/indexes;
- downgrade to `0004` and re-upgrade to `0005`;
- downgrade to base and full re-upgrade;
- `alembic check` without metadata drift.

## Commands

```powershell
cd backend
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run python -m pytest -q
uv run python -m pytest tests/unit/test_task_workflow.py -q
uv run python -m pytest tests/integration/test_task_api.py -q
uv run python -m pytest tests/integration/test_task_concurrency.py -q
uv run python -m pytest tests/integration/test_tool_api.py -q
uv run python -m pytest tests/integration/test_migrations.py -q
uv run python -m pytest tests/integration/test_selection_service.py -q
uv run python -m alembic heads
uv run python -m alembic check
```

Frontend contract checks:

```powershell
cd frontend
npm run format:check
npm run lint
npm run typecheck
npm run test:run
npm run build
```

## Platform limits

SQLite validates conditional updates, unique Step sequence, and migration reversibility
for local development. It is not proof of PostgreSQL lock scheduling under production
load. Before deployment, run concurrent run/resume/retry and stale-lease recovery tests
against the supported PostgreSQL version.

The current runtime identifies stale running tasks through heartbeat/lease timestamps
but does not auto-reclaim them. Confirmation completion also requires explicit resume;
there is no queue, Celery worker, Redis, WebSocket, or background recovery daemon.
