import sqlite3

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


def test_alembic_upgrade_downgrade_upgrade(monkeypatch, tmp_path):
    database_path = tmp_path / "migration.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path}")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-only-jwt-secret-with-at-least-32-characters")
    clear_settings_cache()
    config = Config("alembic.ini")

    command.upgrade(config, "head")
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

    command.downgrade(config, "base")
    assert "users" not in table_names(database_path)

    command.upgrade(config, "head")
    assert "operation_logs" in table_names(database_path)
    assert "product_selection_results" in table_names(database_path)
    assert "product_content_versions" in table_names(database_path)
    command.check(config)
    clear_settings_cache()
