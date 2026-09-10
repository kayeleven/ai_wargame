"""Temporary shared timeline read store."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "memory_timeline",
        sa.Column(
            "id",
            sa.Uuid(),
            sa.ForeignKey("development_artifact.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
    )
    op.create_table(
        "memory_revision",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.Uuid(),
            sa.ForeignKey("memory_timeline.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("record_id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("valid_from", sa.BigInteger(), nullable=False),
        sa.Column("valid_to", sa.BigInteger()),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", sa.Uuid()),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("dataset_id", "source_id"),
    )
    op.create_index(
        "ix_memory_scope", "memory_revision", ["dataset_id", "game_id", "branch_id", "recorded_at"]
    )
    op.create_table(
        "memory_disclosure",
        sa.Column(
            "revision_id",
            sa.Uuid(),
            sa.ForeignKey("memory_revision.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("audience", sa.String(), primary_key=True),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("memory_disclosure")
    op.drop_table("memory_revision")
    op.drop_table("memory_timeline")
