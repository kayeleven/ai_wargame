"""Permanent scenario-independent temporal memory read model.

The 1B tables are a derived projection, so this development transition deliberately
drops them.  Staged source artifacts remain intact and receive an explicit rebuild
state before a package is loaded into the new projection.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("memory_disclosure")
    op.drop_index("ix_memory_scope", table_name="memory_revision")
    op.drop_table("memory_revision")
    op.drop_table("memory_timeline")

    op.create_table(
        "memory_rebuild_state",
        sa.Column(
            "artifact_id",
            sa.Uuid(),
            sa.ForeignKey("development_artifact.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("detail", sa.String(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'loaded')", name="status"),
    )
    op.execute(
        "INSERT INTO memory_rebuild_state (artifact_id, status, detail) "
        "SELECT id, 'pending', 'Derived memory requires explicit reload after migration 0003' "
        "FROM development_artifact"
    )
    op.create_table(
        "memory_dataset",
        sa.Column(
            "id",
            sa.Uuid(),
            sa.ForeignKey("development_artifact.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("package_id", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("root_branch_id", sa.String(), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("id", "game_id", name="uq_memory_dataset_id_game"),
        sa.UniqueConstraint("id", "game_id", "root_branch_id", name="uq_memory_dataset_root"),
    )
    op.create_table(
        "memory_game",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id", "id"],
            ["memory_dataset.id", "memory_dataset.game_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("dataset_id", "id"),
    )
    op.create_table(
        "memory_branch",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("parent_id", sa.String()),
        sa.ForeignKeyConstraint(
            ["dataset_id", "game_id"],
            ["memory_game.dataset_id", "memory_game.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id", "game_id", "parent_id"],
            ["memory_branch.dataset_id", "memory_branch.game_id", "memory_branch.id"],
        ),
        sa.PrimaryKeyConstraint("dataset_id", "game_id", "id"),
    )
    op.create_table(
        "memory_visibility_scope",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id", "game_id"],
            ["memory_game.dataset_id", "memory_game.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("dataset_id", "game_id", "id"),
    )
    op.create_table(
        "memory_record",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("type_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id", "game_id", "branch_id"],
            ["memory_branch.dataset_id", "memory_branch.game_id", "memory_branch.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("dataset_id", "external_id", name="uq_memory_record_external"),
        sa.UniqueConstraint(
            "id", "dataset_id", "game_id", "branch_id", name="uq_memory_record_owner"
        ),
    )
    op.create_table(
        "memory_record_revision",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("ingestion_order", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.BigInteger(), nullable=False),
        sa.Column("valid_to", sa.BigInteger()),
        sa.Column("supersedes_revision_id", sa.Uuid()),
        sa.Column("body", postgresql.JSONB(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["record_id", "dataset_id", "game_id", "branch_id"],
            [
                "memory_record.id",
                "memory_record.dataset_id",
                "memory_record.game_id",
                "memory_record.branch_id",
            ],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id", "record_id"],
            ["memory_record_revision.id", "memory_record_revision.record_id"],
        ),
        sa.CheckConstraint("valid_to IS NULL OR valid_from < valid_to", name="valid_interval"),
        sa.UniqueConstraint("dataset_id", "external_id", name="uq_memory_record_revision_external"),
        sa.UniqueConstraint("id", "record_id", name="uq_memory_record_revision_identity"),
        sa.UniqueConstraint("id", "dataset_id", "game_id", name="uq_memory_record_revision_owner"),
        sa.UniqueConstraint(
            "dataset_id", "ingestion_order", name="uq_memory_record_revision_ingestion"
        ),
    )
    op.create_index(
        "ix_memory_record_temporal",
        "memory_record_revision",
        ["dataset_id", "game_id", "branch_id", "recorded_at", "id"],
    )
    op.execute(
        "CREATE INDEX ix_memory_record_search ON memory_record_revision "
        "USING gin (to_tsvector('simple', body::text))"
    )
    op.create_table(
        "memory_record_disclosure",
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("scope_id", sa.String(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id", "game_id", "scope_id"],
            [
                "memory_visibility_scope.dataset_id",
                "memory_visibility_scope.game_id",
                "memory_visibility_scope.id",
            ],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "dataset_id", "game_id"],
            [
                "memory_record_revision.id",
                "memory_record_revision.dataset_id",
                "memory_record_revision.game_id",
            ],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("revision_id", "scope_id"),
    )
    op.create_table(
        "memory_declared_reference",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "revision_id",
            sa.Uuid(),
            sa.ForeignKey("memory_record_revision.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("target_kind", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("json_pointer", sa.String()),
        sa.CheckConstraint("target_kind IN ('record', 'action', 'external')", name="target_kind"),
        sa.UniqueConstraint(
            "revision_id",
            "purpose",
            "target_kind",
            "target_id",
            "json_pointer",
            name="uq_memory_declared_reference",
        ),
    )
    op.create_table(
        "memory_relationship",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("type_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id", "game_id", "branch_id"],
            ["memory_branch.dataset_id", "memory_branch.game_id", "memory_branch.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("dataset_id", "external_id", name="uq_memory_relationship_external"),
        sa.UniqueConstraint(
            "id", "dataset_id", "game_id", "branch_id", name="uq_memory_relationship_owner"
        ),
    )
    op.create_table(
        "memory_relationship_revision",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("relationship_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("branch_id", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("ingestion_order", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.BigInteger(), nullable=False),
        sa.Column("valid_to", sa.BigInteger()),
        sa.Column("supersedes_revision_id", sa.Uuid()),
        sa.Column("body", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["relationship_id", "dataset_id", "game_id", "branch_id"],
            [
                "memory_relationship.id",
                "memory_relationship.dataset_id",
                "memory_relationship.game_id",
                "memory_relationship.branch_id",
            ],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id", "relationship_id"],
            ["memory_relationship_revision.id", "memory_relationship_revision.relationship_id"],
        ),
        sa.CheckConstraint("valid_to IS NULL OR valid_from < valid_to", name="valid_interval"),
        sa.UniqueConstraint(
            "dataset_id", "external_id", name="uq_memory_relationship_revision_external"
        ),
        sa.UniqueConstraint(
            "id", "relationship_id", name="uq_memory_relationship_revision_identity"
        ),
        sa.UniqueConstraint(
            "id", "dataset_id", "game_id", name="uq_memory_relationship_revision_owner"
        ),
    )
    op.create_table(
        "memory_relationship_disclosure",
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("scope_id", sa.String(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id", "game_id", "scope_id"],
            [
                "memory_visibility_scope.dataset_id",
                "memory_visibility_scope.game_id",
                "memory_visibility_scope.id",
            ],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id", "dataset_id", "game_id"],
            [
                "memory_relationship_revision.id",
                "memory_relationship_revision.dataset_id",
                "memory_relationship_revision.game_id",
            ],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("revision_id", "scope_id"),
    )
    op.create_table(
        "memory_relationship_endpoint",
        sa.Column(
            "revision_id",
            sa.Uuid(),
            sa.ForeignKey("memory_relationship_revision.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.String(), nullable=False),
        sa.Column("target_kind", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.CheckConstraint("position >= 0", name="position"),
        sa.CheckConstraint("target_kind IN ('record', 'action', 'external')", name="target_kind"),
    )


def downgrade() -> None:
    for table in (
        "memory_relationship_endpoint",
        "memory_relationship_disclosure",
        "memory_relationship_revision",
        "memory_relationship",
        "memory_declared_reference",
        "memory_record_disclosure",
        "memory_record_revision",
        "memory_record",
        "memory_visibility_scope",
        "memory_branch",
        "memory_game",
        "memory_dataset",
        "memory_rebuild_state",
    ):
        op.drop_table(table)
    # Restore an empty 1B projection; staged artifacts remain available.
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
        "ix_memory_scope",
        "memory_revision",
        ["dataset_id", "game_id", "branch_id", "recorded_at"],
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
