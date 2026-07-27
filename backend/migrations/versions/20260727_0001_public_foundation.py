"""Create public backend foundation tables.

Revision ID: 20260727_0001
Revises:
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

revision: str = "20260727_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "agent_tasks",
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("user_input", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step", sa.String(length=100), nullable=True),
        sa.Column("result", JSON_TYPE, nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_agent_tasks_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_tasks")),
    )
    op.create_index(
        "ix_agent_tasks_created_by_created_at",
        "agent_tasks",
        ["created_by", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_agent_tasks_status_created_at",
        "agent_tasks",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "agent_task_steps",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("step_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_summary", JSON_TYPE, nullable=True),
        sa.Column("output_summary", JSON_TYPE, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["agent_tasks.id"],
            name=op.f("fk_agent_task_steps_task_id_agent_tasks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_task_steps")),
    )
    op.create_index(
        "ix_agent_task_steps_task_id_status",
        "agent_task_steps",
        ["task_id", "status"],
        unique=False,
    )

    op.create_table(
        "tool_calls",
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_summary", JSON_TYPE, nullable=True),
        sa.Column("output_summary", JSON_TYPE, nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["agent_tasks.id"],
            name=op.f("fk_tool_calls_task_id_agent_tasks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_calls")),
    )
    op.create_index(
        "ix_tool_calls_task_id_created_at",
        "tool_calls",
        ["task_id", "created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_tool_calls_tool_name"), "tool_calls", ["tool_name"], unique=False)

    op.create_table(
        "confirmation_tasks",
        sa.Column("agent_task_id", sa.Uuid(), nullable=False),
        sa.Column("operation_type", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.String(length=255), nullable=True),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("before_snapshot", JSON_TYPE, nullable=True),
        sa.Column("after_snapshot", JSON_TYPE, nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_result", JSON_TYPE, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_task_id"],
            ["agent_tasks.id"],
            name=op.f("fk_confirmation_tasks_agent_task_id_agent_tasks"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by"],
            ["users.id"],
            name=op.f("fk_confirmation_tasks_confirmed_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_confirmation_tasks_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_confirmation_tasks")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_confirmation_tasks_idempotency_key")),
    )
    op.create_index(
        "ix_confirmation_tasks_agent_task_id",
        "confirmation_tasks",
        ["agent_task_id"],
        unique=False,
    )
    op.create_index(
        "ix_confirmation_tasks_status_created_at",
        "confirmation_tasks",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "operation_logs",
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.String(length=255), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("agent_task_id", sa.Uuid(), nullable=True),
        sa.Column("confirmation_task_id", sa.Uuid(), nullable=True),
        sa.Column("before_snapshot", JSON_TYPE, nullable=True),
        sa.Column("after_snapshot", JSON_TYPE, nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_operation_logs_actor_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["agent_task_id"],
            ["agent_tasks.id"],
            name=op.f("fk_operation_logs_agent_task_id_agent_tasks"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["confirmation_task_id"],
            ["confirmation_tasks.id"],
            name=op.f("fk_operation_logs_confirmation_task_id_confirmation_tasks"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_operation_logs")),
    )
    op.create_index("ix_operation_logs_created_at", "operation_logs", ["created_at"], unique=False)
    op.create_index("ix_operation_logs_request_id", "operation_logs", ["request_id"], unique=False)
    op.create_index(
        "ix_operation_logs_target",
        "operation_logs",
        ["target_type", "target_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_operation_logs_target", table_name="operation_logs")
    op.drop_index("ix_operation_logs_request_id", table_name="operation_logs")
    op.drop_index("ix_operation_logs_created_at", table_name="operation_logs")
    op.drop_table("operation_logs")

    op.drop_index("ix_confirmation_tasks_status_created_at", table_name="confirmation_tasks")
    op.drop_index("ix_confirmation_tasks_agent_task_id", table_name="confirmation_tasks")
    op.drop_table("confirmation_tasks")

    op.drop_index(op.f("ix_tool_calls_tool_name"), table_name="tool_calls")
    op.drop_index("ix_tool_calls_task_id_created_at", table_name="tool_calls")
    op.drop_table("tool_calls")

    op.drop_index("ix_agent_task_steps_task_id_status", table_name="agent_task_steps")
    op.drop_table("agent_task_steps")

    op.drop_index("ix_agent_tasks_status_created_at", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_created_by_created_at", table_name="agent_tasks")
    op.drop_table("agent_tasks")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
