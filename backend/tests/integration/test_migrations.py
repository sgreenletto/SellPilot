import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from alembic import command
from alembic.config import Config

from sellpilot.core.config import clear_settings_cache


def table_names(database_path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def column_names(database_path, table_name: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return {row[1] for row in rows}


def foreign_key_actions(database_path, table_names_to_check: set[str]) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = [
            row
            for table_name in table_names_to_check
            for row in connection.execute(f'PRAGMA foreign_key_list("{table_name}")').fetchall()
        ]
    return {row[6] for row in rows}


def unique_index_columns(database_path, table_name: str) -> set[tuple[str, ...]]:
    with sqlite3.connect(database_path) as connection:
        indexes = connection.execute(f'PRAGMA index_list("{table_name}")').fetchall()
        return {
            tuple(
                row[2] for row in connection.execute(f'PRAGMA index_info("{index[1]}")').fetchall()
            )
            for index in indexes
            if index[2] == 1
        }


def insert_pre_runtime_rows(database_path) -> tuple[str, str]:
    user_id = uuid4().hex
    task_id = uuid4().hex
    confirmation_id = uuid4().hex
    tool_call_id = uuid4().hex
    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO users
                (username, password_hash, role, is_active, id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("migration-user", "test-hash", "ADMIN", 1, user_id, now, now),
        )
        connection.execute(
            """
            INSERT INTO agent_tasks
                (task_type, user_input, status, retry_count, created_by, created_at, id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("diagnostic", "legacy task", "PENDING", 0, user_id, now, task_id),
        )
        connection.execute(
            """
            INSERT INTO confirmation_tasks
                (
                    agent_task_id, operation_type, target_type, risk_level, status,
                    idempotency_key, created_by, created_at, id
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                "legacy.write",
                "legacy-target",
                "WRITE",
                "PENDING",
                "legacy-idempotency-key",
                user_id,
                now,
                confirmation_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO tool_calls
                (task_id, tool_name, risk_level, status, created_at, id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, "legacy_tool", "READ", "SUCCEEDED", now, tool_call_id),
        )
    return confirmation_id, tool_call_id


def test_alembic_upgrade_downgrade_upgrade(monkeypatch, tmp_path):
    database_path = tmp_path / "migration.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path}")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-jwt-secret-with-at-least-32-characters")
    clear_settings_cache()
    config = Config("alembic.ini")

    command.upgrade(config, "20260727_0002")
    confirmation_id, tool_call_id = insert_pre_runtime_rows(database_path)
    command.upgrade(config, "20260728_0003")
    assert {
        "users",
        "agent_tasks",
        "agent_task_steps",
        "tool_calls",
        "confirmation_tasks",
        "operation_logs",
        "product_selection_tasks",
        "product_selection_results",
        "review_analysis_results",
        "review_analysis_evidence",
        "product_improvement_reports",
        "product_improvement_suggestions",
        "product_contents",
        "product_content_versions",
        "prompt_templates",
        "prompt_versions",
        "model_invocations",
        "generated_reports",
    }.issubset(table_names(database_path))
    assert {
        "recommendation_reason",
        "risk_warnings",
        "data_completeness",
        "data_sources",
        "source_type",
        "is_mock_data",
    }.issubset(column_names(database_path, "product_selection_results"))
    assert {
        "input_conditions",
        "source_snapshot_version",
    }.issubset(column_names(database_path, "review_analysis_results"))
    assert {
        "translated_excerpt",
        "source_created_at",
        "confidence",
        "source_type",
        "is_mock_data",
    }.issubset(column_names(database_path, "review_analysis_evidence"))
    assert {
        "algorithm_version",
        "data_sources",
        "input_conditions",
        "source_type",
        "is_mock_data",
    }.issubset(column_names(database_path, "product_improvement_reports"))
    assert {
        "source_snapshot_version",
        "agent_task_id",
    }.issubset(column_names(database_path, "product_contents"))
    assert {
        "source_facts_snapshot",
        "change_type",
        "change_summary",
    }.issubset(column_names(database_path, "product_content_versions"))
    assert {
        "task_type",
        "language",
    }.issubset(column_names(database_path, "prompt_templates"))
    assert {"change_summary"}.issubset(column_names(database_path, "prompt_versions"))
    assert {
        "model_parameters",
        "timeout_ms",
        "retry_count",
        "estimated_cost",
        "cost_currency",
        "created_by",
    }.issubset(column_names(database_path, "model_invocations"))
    assert {
        "data_sources",
        "input_conditions",
        "model_invocation_id",
        "agent_task_id",
        "is_mock_data",
        "result_version",
    }.issubset(column_names(database_path, "generated_reports"))
    assert {
        "tool_version",
        "caller_type",
        "caller_name",
        "request_id",
        "user_id",
        "task_step_id",
        "confirmation_id",
        "idempotency_key",
        "input_digest",
        "attempt_history",
        "attempt_count",
        "started_at",
        "completed_at",
    }.issubset(column_names(database_path, "tool_calls"))
    assert {
        "tool_name",
        "tool_version",
        "tool_input",
        "input_digest",
        "request_id",
        "risk_warning",
        "idempotency_scope",
        "execution_started_at",
    }.issubset(column_names(database_path, "confirmation_tasks"))
    assert {
        "tool_call_id",
        "risk_level",
        "caller_type",
        "is_mock",
        "details",
    }.issubset(column_names(database_path, "operation_logs"))
    with sqlite3.connect(database_path) as connection:
        confirmation_row = connection.execute(
            """
            SELECT idempotency_scope
            FROM confirmation_tasks
            WHERE id = ?
            """,
            (confirmation_id,),
        ).fetchone()
        tool_call_row = connection.execute(
            """
            SELECT tool_version, caller_type, request_id, attempt_count, started_at
            FROM tool_calls
            WHERE id = ?
            """,
            (tool_call_id,),
        ).fetchone()
    assert confirmation_row is not None
    assert len(confirmation_row[0]) == 64
    assert tool_call_row is not None
    assert tool_call_row[:4] == (
        "1.0.0",
        "system",
        "00000000-0000-0000-0000-000000000000",
        0,
    )
    assert tool_call_row[4] is not None
    confirmation_unique_indexes = unique_index_columns(
        database_path,
        "confirmation_tasks",
    )
    assert ("idempotency_scope",) in confirmation_unique_indexes
    assert ("idempotency_key",) not in confirmation_unique_indexes
    assert foreign_key_actions(
        database_path,
        {
            "product_selection_tasks",
            "product_selection_results",
            "review_analysis_results",
            "review_analysis_evidence",
            "product_improvement_reports",
            "product_improvement_suggestions",
            "product_contents",
            "product_content_versions",
            "prompt_templates",
            "prompt_versions",
            "model_invocations",
            "generated_reports",
        },
    ) == {"RESTRICT"}

    command.downgrade(config, "20260727_0002")
    assert "idempotency_scope" not in column_names(database_path, "confirmation_tasks")
    assert ("idempotency_key",) in unique_index_columns(
        database_path,
        "confirmation_tasks",
    )

    command.upgrade(config, "20260728_0003")
    assert "idempotency_scope" in column_names(database_path, "confirmation_tasks")
    command.check(config)

    command.downgrade(config, "base")
    assert "users" not in table_names(database_path)

    command.upgrade(config, "head")
    assert "operation_logs" in table_names(database_path)
    assert "product_selection_results" in table_names(database_path)
    assert "product_content_versions" in table_names(database_path)
    command.check(config)
    clear_settings_cache()
