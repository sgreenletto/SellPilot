"""Add persistent task workflow runtime fields.

Revision ID: 20260728_0005
Revises: 20260728_0004
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.sqltypes import Text

revision: str = "20260728_0005"
down_revision: str | Sequence[str] | None = "20260728_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")
ZERO_REQUEST_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    with op.batch_alter_table("agent_tasks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("workflow_name", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("workflow_version", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("workflow_input", JSON_TYPE, nullable=True))
        batch_op.add_column(sa.Column("parent_task_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("current_node", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("serialized_state", JSON_TYPE, nullable=True))
        batch_op.add_column(sa.Column("task_attempt", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("request_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("execution_token", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("runner_id", sa.String(length=100), nullable=True))
        batch_op.add_column(
            sa.Column("execution_started_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_foreign_key(
            op.f("fk_agent_tasks_parent_task_id_agent_tasks"),
            "agent_tasks",
            ["parent_task_id"],
            ["id"],
            ondelete="SET NULL",
        )

    tasks = sa.table(
        "agent_tasks",
        sa.column("id", sa.Uuid()),
        sa.column("task_type", sa.String()),
        sa.column("user_input", sa.Text()),
        sa.column("workflow_name", sa.String()),
        sa.column("workflow_version", sa.String()),
        sa.column("workflow_input", JSON_TYPE),
        sa.column("serialized_state", JSON_TYPE),
        sa.column("task_attempt", sa.Integer()),
        sa.column("request_id", sa.String()),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(tasks.c.id, tasks.c.task_type, tasks.c.user_input)
    ).mappings()
    for row in rows:
        connection.execute(
            tasks.update()
            .where(tasks.c.id == row["id"])
            .values(
                workflow_name=row["task_type"],
                workflow_version="1.0.0",
                workflow_input={"legacy_input": row["user_input"]},
                serialized_state={},
                task_attempt=0,
                request_id=ZERO_REQUEST_ID,
            )
        )

    with op.batch_alter_table("agent_tasks", schema=None) as batch_op:
        batch_op.alter_column("workflow_name", existing_type=sa.String(100), nullable=False)
        batch_op.alter_column("workflow_version", existing_type=sa.String(32), nullable=False)
        batch_op.alter_column("workflow_input", existing_type=JSON_TYPE, nullable=False)
        batch_op.alter_column("serialized_state", existing_type=JSON_TYPE, nullable=False)
        batch_op.alter_column("task_attempt", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("request_id", existing_type=sa.String(64), nullable=False)
        batch_op.create_index(
            "ix_agent_tasks_workflow_status", ["workflow_name", "status"], unique=False
        )
        batch_op.create_index("ix_agent_tasks_parent_task_id", ["parent_task_id"], unique=False)
        batch_op.create_index("ix_agent_tasks_lease_expires_at", ["lease_expires_at"], unique=False)

    with op.batch_alter_table("agent_task_steps", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sequence", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("node_type", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("attempt_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("error_code", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("tool_call_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("confirmation_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("metadata", JSON_TYPE, nullable=True))

    steps = sa.table(
        "agent_task_steps",
        sa.column("id", sa.Uuid()),
        sa.column("task_id", sa.Uuid()),
        sa.column("started_at", sa.DateTime()),
        sa.column("sequence", sa.Integer()),
        sa.column("node_type", sa.String()),
        sa.column("attempt_count", sa.Integer()),
    )
    task_ids = connection.execute(sa.select(steps.c.task_id).distinct()).scalars()
    for task_id in task_ids:
        step_rows = connection.execute(
            sa.select(steps.c.id)
            .where(steps.c.task_id == task_id)
            .order_by(steps.c.started_at.asc(), steps.c.id.asc())
        ).scalars()
        for sequence, step_id in enumerate(step_rows, start=1):
            connection.execute(
                steps.update()
                .where(steps.c.id == step_id)
                .values(sequence=sequence, node_type="action", attempt_count=0)
            )

    with op.batch_alter_table("agent_task_steps", schema=None) as batch_op:
        batch_op.alter_column("sequence", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("node_type", existing_type=sa.String(32), nullable=False)
        batch_op.alter_column("attempt_count", existing_type=sa.Integer(), nullable=False)
        batch_op.create_index("ix_agent_task_steps_tool_call_id", ["tool_call_id"], unique=False)
        batch_op.create_index(
            "ix_agent_task_steps_confirmation_id", ["confirmation_id"], unique=False
        )
        batch_op.create_unique_constraint(
            "uq_agent_task_steps_task_sequence", ["task_id", "sequence"]
        )

    with op.batch_alter_table("confirmation_tasks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("task_step_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_confirmation_tasks_task_step_id_agent_task_steps"),
            "agent_task_steps",
            ["task_step_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_confirmation_tasks_task_step_id", ["task_step_id"], unique=False)

    with op.batch_alter_table("operation_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("task_step_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_operation_logs_task_step_id_agent_task_steps"),
            "agent_task_steps",
            ["task_step_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_operation_logs_task_step_id", ["task_step_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("operation_logs", schema=None) as batch_op:
        batch_op.drop_index("ix_operation_logs_task_step_id")
        batch_op.drop_constraint(
            op.f("fk_operation_logs_task_step_id_agent_task_steps"),
            type_="foreignkey",
        )
        batch_op.drop_column("task_step_id")

    with op.batch_alter_table("confirmation_tasks", schema=None) as batch_op:
        batch_op.drop_index("ix_confirmation_tasks_task_step_id")
        batch_op.drop_constraint(
            op.f("fk_confirmation_tasks_task_step_id_agent_task_steps"),
            type_="foreignkey",
        )
        batch_op.drop_column("task_step_id")

    with op.batch_alter_table("agent_task_steps", schema=None) as batch_op:
        batch_op.drop_constraint("uq_agent_task_steps_task_sequence", type_="unique")
        batch_op.drop_index("ix_agent_task_steps_confirmation_id")
        batch_op.drop_index("ix_agent_task_steps_tool_call_id")
        batch_op.drop_column("metadata")
        batch_op.drop_column("confirmation_id")
        batch_op.drop_column("tool_call_id")
        batch_op.drop_column("error_code")
        batch_op.drop_column("attempt_count")
        batch_op.drop_column("node_type")
        batch_op.drop_column("sequence")

    with op.batch_alter_table("agent_tasks", schema=None) as batch_op:
        batch_op.drop_index("ix_agent_tasks_lease_expires_at")
        batch_op.drop_index("ix_agent_tasks_parent_task_id")
        batch_op.drop_index("ix_agent_tasks_workflow_status")
        batch_op.drop_constraint(
            op.f("fk_agent_tasks_parent_task_id_agent_tasks"),
            type_="foreignkey",
        )
        batch_op.drop_column("lease_expires_at")
        batch_op.drop_column("heartbeat_at")
        batch_op.drop_column("execution_started_at")
        batch_op.drop_column("runner_id")
        batch_op.drop_column("execution_token")
        batch_op.drop_column("request_id")
        batch_op.drop_column("task_attempt")
        batch_op.drop_column("serialized_state")
        batch_op.drop_column("current_node")
        batch_op.drop_column("parent_task_id")
        batch_op.drop_column("workflow_input")
        batch_op.drop_column("workflow_version")
        batch_op.drop_column("workflow_name")
