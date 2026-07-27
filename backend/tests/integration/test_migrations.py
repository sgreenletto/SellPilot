import sqlite3

from alembic import command
from alembic.config import Config

from sellpilot.core.config import clear_settings_cache


def table_names(database_path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


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
    }.issubset(table_names(database_path))

    command.downgrade(config, "base")
    assert "users" not in table_names(database_path)

    command.upgrade(config, "head")
    assert "operation_logs" in table_names(database_path)
    command.check(config)
    clear_settings_cache()
