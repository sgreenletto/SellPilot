import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import asyncpg
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

from sellpilot.core.config import clear_settings_cache
from tests.postgres import reset_test_schema


async def _query(database_url: str, statement: str, *parameters):
    url = make_url(database_url)
    connection = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port or 5432,
        database=url.database,
    )
    try:
        return await connection.fetch(statement, *parameters)
    finally:
        await connection.close()


def query(database_url: str, statement: str, *parameters):
    return asyncio.run(_query(database_url, statement, *parameters))


def table_names(database_url: str) -> set[str]:
    rows = query(
        database_url,
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """,
    )
    return {row["table_name"] for row in rows}


def column_names(database_url: str, table_name: str) -> set[str]:
    rows = query(
        database_url,
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        """,
        table_name,
    )
    return {row["column_name"] for row in rows}


def unique_index_columns(database_url: str, table_name: str) -> set[tuple[str, ...]]:
    rows = query(
        database_url,
        """
        SELECT array_agg(attribute.attname ORDER BY key.ordinality) AS columns
        FROM pg_index AS index
        JOIN pg_class AS relation ON relation.oid = index.indrelid
        JOIN LATERAL unnest(index.indkey) WITH ORDINALITY AS key(attnum, ordinality)
          ON true
        JOIN pg_attribute AS attribute
          ON attribute.attrelid = relation.oid AND attribute.attnum = key.attnum
        WHERE relation.relname = $1 AND index.indisunique
        GROUP BY index.indexrelid
        """,
        table_name,
    )
    return {tuple(row["columns"]) for row in rows}


def foreign_key_actions(database_url: str, tables: set[str]) -> set[str]:
    rows = query(
        database_url,
        """
        SELECT delete_rule
        FROM information_schema.referential_constraints
        WHERE constraint_schema = 'public'
          AND constraint_name IN (
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_schema = 'public'
              AND table_name = ANY($1::text[])
              AND constraint_type = 'FOREIGN KEY'
          )
        """,
        list(tables),
    )
    return {row["delete_rule"] for row in rows}


def insert_pre_runtime_rows(database_url: str) -> tuple[UUID, UUID, UUID, UUID]:
    user_id = uuid4()
    task_id = uuid4()
    confirmation_id = uuid4()
    tool_call_id = uuid4()
    step_id = uuid4()
    operation_log_id = uuid4()
    now = datetime.now(UTC)
    query(
        database_url,
        """
        INSERT INTO users
            (username, password_hash, role, is_active, id, created_at, updated_at)
        VALUES ('migration-user', 'test-hash', 'ADMIN', true, $1, $2, $2)
        """,
        user_id,
        now,
    )
    query(
        database_url,
        """
        INSERT INTO agent_tasks
            (task_type, user_input, status, retry_count, created_by, created_at, id)
        VALUES ('diagnostic', 'legacy task', 'PENDING', 0, $1, $2, $3)
        """,
        user_id,
        now,
        task_id,
    )
    query(
        database_url,
        """
        INSERT INTO agent_task_steps
            (task_id, step_name, status, started_at, id)
        VALUES ($1, 'legacy-step', 'SUCCEEDED', $2, $3)
        """,
        task_id,
        now,
        step_id,
    )
    query(
        database_url,
        """
        INSERT INTO confirmation_tasks
            (agent_task_id, operation_type, target_type, risk_level, status,
             idempotency_key, created_by, created_at, id)
        VALUES ($1, 'legacy.write', 'legacy-target', 'WRITE', 'PENDING',
                'legacy-idempotency-key', $2, $3, $4)
        """,
        task_id,
        user_id,
        now,
        confirmation_id,
    )
    query(
        database_url,
        """
        INSERT INTO tool_calls
            (task_id, tool_name, risk_level, status, created_at, id)
        VALUES ($1, 'legacy_tool', 'READ', 'SUCCEEDED', $2, $3)
        """,
        task_id,
        now,
        tool_call_id,
    )
    query(
        database_url,
        """
        INSERT INTO operation_logs
            (actor_id, action, target_type, request_id, agent_task_id, status, created_at, id)
        VALUES ($1, 'legacy.action', 'legacy-target',
                '00000000-0000-0000-0000-000000000000', $2, 'SUCCEEDED', $3, $4)
        """,
        user_id,
        task_id,
        now,
        operation_log_id,
    )
    return confirmation_id, tool_call_id, step_id, operation_log_id


def test_alembic_upgrade_downgrade_upgrade(
    monkeypatch,
    postgres_test_database_url: str,
):
    reset_test_schema(postgres_test_database_url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", postgres_test_database_url)
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-only-jwt-secret-with-at-least-32-characters",
    )
    clear_settings_cache()
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    revisions = list(script.walk_revisions())
    revision_ids = [item.revision for item in revisions]
    assert len(revision_ids) == len(set(revision_ids))
    assert script.get_heads() == ["20260728_0007"]
    assert all(
        item.down_revision is None or script.get_revision(item.down_revision) is not None
        for item in revisions
    )

    command.upgrade(config, "20260727_0002")
    confirmation_id, tool_call_id, step_id, operation_log_id = insert_pre_runtime_rows(
        postgres_test_database_url
    )
    command.upgrade(config, "20260728_0004")

    assert {
        "users",
        "agent_tasks",
        "agent_task_steps",
        "tool_calls",
        "confirmation_tasks",
        "operation_logs",
        "product_selection_tasks",
        "review_analysis_results",
        "product_contents",
        "prompt_templates",
        "model_invocations",
        "products",
        "orders",
        "reviews",
        "category_trends",
    }.issubset(table_names(postgres_test_database_url))
    assert {
        "tool_version",
        "caller_type",
        "request_id",
        "attempt_count",
        "started_at",
    }.issubset(column_names(postgres_test_database_url, "tool_calls"))
    assert {
        "idempotency_scope",
        "execution_started_at",
    }.issubset(column_names(postgres_test_database_url, "confirmation_tasks"))
    assert ("idempotency_scope",) in unique_index_columns(
        postgres_test_database_url,
        "confirmation_tasks",
    )
    assert ("idempotency_key",) not in unique_index_columns(
        postgres_test_database_url,
        "confirmation_tasks",
    )
    assert foreign_key_actions(
        postgres_test_database_url,
        {
            "product_selection_tasks",
            "review_analysis_results",
            "product_contents",
            "prompt_templates",
            "model_invocations",
        },
    ) == {"RESTRICT"}

    migrated = query(
        postgres_test_database_url,
        """
        SELECT c.idempotency_scope, t.tool_version, t.caller_type, t.attempt_count
        FROM confirmation_tasks AS c
        JOIN tool_calls AS t ON t.id = $2
        WHERE c.id = $1
        """,
        confirmation_id,
        tool_call_id,
    )[0]
    assert len(migrated["idempotency_scope"]) == 64
    assert (
        migrated["tool_version"],
        migrated["caller_type"],
        migrated["attempt_count"],
    ) == ("1.0.0", "system", 0)

    command.upgrade(config, "20260728_0006")
    assert {
        "workflow_name",
        "workflow_version",
        "serialized_state",
        "execution_token",
        "lease_expires_at",
    }.issubset(column_names(postgres_test_database_url, "agent_tasks"))
    assert {
        "sequence",
        "node_type",
        "attempt_count",
        "tool_call_id",
        "confirmation_id",
    }.issubset(column_names(postgres_test_database_url, "agent_task_steps"))
    assert ("task_id", "sequence") in unique_index_columns(
        postgres_test_database_url,
        "agent_task_steps",
    )
    assert query(
        postgres_test_database_url,
        "SELECT sequence, node_type FROM agent_task_steps WHERE id = $1",
        step_id,
    )[0] == (1, "action")
    assert (
        query(
            postgres_test_database_url,
            "SELECT task_step_id FROM operation_logs WHERE id = $1",
            operation_log_id,
        )[0]["task_step_id"]
        is None
    )

    command.downgrade(config, "20260728_0004")
    assert "workflow_name" not in column_names(postgres_test_database_url, "agent_tasks")
    command.upgrade(config, "20260728_0007")
    command.check(config)
    assert "knowledge_documents" in table_names(postgres_test_database_url)

    command.downgrade(config, "base")
    assert "users" not in table_names(postgres_test_database_url)
    command.upgrade(config, "head")
    command.check(config)
    assert "category_trends" in table_names(postgres_test_database_url)
    reset_test_schema(postgres_test_database_url)
    clear_settings_cache()
