"""Persist market selection candidates.

Revision ID: 20260728_0005
Revises: 20260728_0004
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0005"
down_revision: str | Sequence[str] | None = "20260728_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "selection_candidates",
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("product_external_id", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("title_snapshot", sa.String(length=500), nullable=False),
        sa.Column("is_mock_data", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_by", "product_external_id", name="uq_candidate_user_product"),
    )
    op.create_index(
        "ix_selection_candidates_user_created",
        "selection_candidates",
        ["created_by", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_selection_candidates_user_created", table_name="selection_candidates")
    op.drop_table("selection_candidates")
