"""Create knowledge base tables.

Revision ID: 20260728_0007
Revises: 20260728_0006
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

revision: str = "20260728_0007"
down_revision: str | Sequence[str] | None = "20260728_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("metadata_json", JSON_TYPE, nullable=False),
        sa.Column("is_mock_data", sa.Boolean(), nullable=False),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_documents_category_status",
        "knowledge_documents",
        ["category", "status"],
    )
    op.create_index(
        "ix_knowledge_documents_created_by",
        "knowledge_documents",
        ["created_by"],
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("embedding_status", sa.String(length=32), nullable=False),
        sa.Column("chroma_id", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", JSON_TYPE, nullable=False),
        sa.Column("is_mock_data", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_chunks_document_id",
        "knowledge_chunks",
        ["document_id"],
    )
    op.create_index(
        "ix_knowledge_chunks_embedding_status",
        "knowledge_chunks",
        ["embedding_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_embedding_status", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_knowledge_documents_created_by", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_category_status", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
