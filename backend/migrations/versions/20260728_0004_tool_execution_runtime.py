"""Add audited tool execution runtime fields.

Revision ID: 20260728_0004
Revises: 20260728_0003
Create Date: 2026-07-28
"""

import hashlib
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.sqltypes import Text

revision: str = "20260728_0004"
down_revision: str | Sequence[str] | None = "20260728_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")


def _idempotency_scope(row: RowMapping) -> str:
    canonical = json.dumps(
        {
            "created_by": str(row["created_by"]),
            "operation_type": row["operation_type"],
            "tool_name": row["tool_name"],
            "tool_version": row["tool_version"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "idempotency_key": row["idempotency_key"],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def upgrade() -> None:
    with op.batch_alter_table("confirmation_tasks", schema=None) as batch_op:
        batch_op.drop_constraint(
            op.f("uq_confirmation_tasks_idempotency_key"),
            type_="unique",
        )
        batch_op.add_column(sa.Column("tool_name", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("tool_version", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("tool_input", JSON_TYPE, nullable=True))
        batch_op.add_column(sa.Column("input_digest", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("request_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("risk_warning", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("idempotency_scope", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("execution_started_at", sa.DateTime(timezone=True), nullable=True)
        )

    confirmation_tasks = sa.table(
        "confirmation_tasks",
        sa.column("id", sa.Uuid()),
        sa.column("created_by", sa.Uuid()),
        sa.column("operation_type", sa.String()),
        sa.column("tool_name", sa.String()),
        sa.column("tool_version", sa.String()),
        sa.column("target_type", sa.String()),
        sa.column("target_id", sa.String()),
        sa.column("idempotency_key", sa.String()),
        sa.column("idempotency_scope", sa.String()),
    )
    connection = op.get_bind()
    legacy_rows = connection.execute(
        sa.select(
            confirmation_tasks.c.id,
            confirmation_tasks.c.created_by,
            confirmation_tasks.c.operation_type,
            confirmation_tasks.c.tool_name,
            confirmation_tasks.c.tool_version,
            confirmation_tasks.c.target_type,
            confirmation_tasks.c.target_id,
            confirmation_tasks.c.idempotency_key,
        )
    ).mappings()
    for row in legacy_rows:
        connection.execute(
            confirmation_tasks.update()
            .where(confirmation_tasks.c.id == row["id"])
            .values(idempotency_scope=_idempotency_scope(row))
        )

    with op.batch_alter_table("confirmation_tasks", schema=None) as batch_op:
        batch_op.alter_column(
            "idempotency_scope",
            existing_type=sa.String(length=64),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            op.f("uq_confirmation_tasks_idempotency_scope"),
            ["idempotency_scope"],
        )
        batch_op.create_index(
            "ix_confirmation_tasks_status_execution_started_at",
            ["status", "execution_started_at"],
            unique=False,
        )

    with op.batch_alter_table("tool_calls", schema=None) as batch_op:
        batch_op.add_column(sa.Column("task_step_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("confirmation_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "tool_version",
                sa.String(length=32),
                server_default="1.0.0",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "caller_type",
                sa.String(length=32),
                server_default="system",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("caller_name", sa.String(length=100), nullable=True))
        batch_op.add_column(
            sa.Column(
                "request_id",
                sa.String(length=64),
                server_default="00000000-0000-0000-0000-000000000000",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("input_digest", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("attempt_history", JSON_TYPE, nullable=True))
        batch_op.add_column(
            sa.Column(
                "attempt_count",
                sa.Integer(),
                server_default="0",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_tool_calls_task_step_id_agent_task_steps"),
            "agent_task_steps",
            ["task_step_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            op.f("fk_tool_calls_confirmation_id_confirmation_tasks"),
            "confirmation_tasks",
            ["confirmation_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            op.f("fk_tool_calls_user_id_users"),
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_tool_calls_status_created_at",
            ["status", "created_at"],
            unique=False,
        )
        batch_op.create_index("ix_tool_calls_request_id", ["request_id"], unique=False)
        batch_op.create_index(
            "ix_tool_calls_confirmation_id",
            ["confirmation_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_tool_calls_idempotency_key",
            ["idempotency_key"],
            unique=False,
        )

    with op.batch_alter_table("operation_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tool_call_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("risk_level", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("caller_type", sa.String(length=32), nullable=True))
        batch_op.add_column(
            sa.Column("is_mock", sa.Boolean(), server_default=sa.false(), nullable=False)
        )
        batch_op.add_column(sa.Column("details", JSON_TYPE, nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_operation_logs_tool_call_id_tool_calls"),
            "tool_calls",
            ["tool_call_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("operation_logs", schema=None) as batch_op:
        batch_op.drop_constraint(
            op.f("fk_operation_logs_tool_call_id_tool_calls"),
            type_="foreignkey",
        )
        batch_op.drop_column("details")
        batch_op.drop_column("is_mock")
        batch_op.drop_column("caller_type")
        batch_op.drop_column("risk_level")
        batch_op.drop_column("tool_call_id")

    with op.batch_alter_table("tool_calls", schema=None) as batch_op:
        batch_op.drop_index("ix_tool_calls_idempotency_key")
        batch_op.drop_index("ix_tool_calls_confirmation_id")
        batch_op.drop_index("ix_tool_calls_request_id")
        batch_op.drop_index("ix_tool_calls_status_created_at")
        batch_op.drop_constraint(
            op.f("fk_tool_calls_user_id_users"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_tool_calls_confirmation_id_confirmation_tasks"),
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            op.f("fk_tool_calls_task_step_id_agent_task_steps"),
            type_="foreignkey",
        )
        batch_op.drop_column("completed_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("attempt_count")
        batch_op.drop_column("attempt_history")
        batch_op.drop_column("input_digest")
        batch_op.drop_column("idempotency_key")
        batch_op.drop_column("request_id")
        batch_op.drop_column("caller_name")
        batch_op.drop_column("caller_type")
        batch_op.drop_column("tool_version")
        batch_op.drop_column("user_id")
        batch_op.drop_column("confirmation_id")
        batch_op.drop_column("task_step_id")

    with op.batch_alter_table("confirmation_tasks", schema=None) as batch_op:
        batch_op.drop_index("ix_confirmation_tasks_status_execution_started_at")
        batch_op.drop_constraint(
            op.f("uq_confirmation_tasks_idempotency_scope"),
            type_="unique",
        )
        batch_op.drop_column("execution_started_at")
        batch_op.drop_column("idempotency_scope")
        batch_op.drop_column("risk_warning")
        batch_op.drop_column("request_id")
        batch_op.drop_column("input_digest")
        batch_op.drop_column("tool_input")
        batch_op.drop_column("tool_version")
        batch_op.drop_column("tool_name")
        batch_op.create_unique_constraint(
            op.f("uq_confirmation_tasks_idempotency_key"),
            ["idempotency_key"],
        )
