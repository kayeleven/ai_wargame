"""Phase 1D workspace and operational-memory ownership.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _require_empty_0004() -> None:
    bind = op.get_bind()
    for table in sa.inspect(bind).get_table_names(schema="public"):
        if table == "alembic_version":
            continue
        quoted = bind.dialect.identifier_preparer.quote(table)
        if bind.scalar(sa.text(f"SELECT EXISTS (SELECT 1 FROM {quoted} LIMIT 1)")):
            raise RuntimeError(
                "0005 supports only an empty 0004 schema; recreate the database before upgrading"
            )


def upgrade() -> None:
    _require_empty_0004()
    # Register referenced 0001–4 tables too; ``create_all`` is restricted to
    # workspace tables below, but SQLAlchemy still needs FK targets in metadata.
    import living_memory.administration  # noqa: F401
    import living_memory.identity  # noqa: F401
    import living_memory.memory  # noqa: F401
    from living_memory.workspace import Base

    bind = op.get_bind()
    Base.metadata.create_all(
        bind,
        tables=[table for table in Base.metadata.sorted_tables if table.name.startswith("ws_")],
    )
    op.add_column(
        "memory_dataset",
        sa.Column("source_kind", sa.String(), nullable=False, server_default="staged"),
    )
    op.add_column("memory_dataset", sa.Column("admin_game_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_memory_dataset_admin_game_id_admin_game",
        "memory_dataset",
        "admin_game",
        ["admin_game_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        "ck_memory_dataset_source_kind",
        "memory_dataset",
        "source_kind IN ('staged', 'operational')",
    )
    op.create_check_constraint(
        "ck_memory_dataset_operational_owner",
        "memory_dataset",
        "(source_kind = 'staged' AND admin_game_id IS NULL) OR "
        "(source_kind = 'operational' AND admin_game_id IS NOT NULL)",
    )
    op.create_unique_constraint(
        "uq_memory_dataset_operational_game", "memory_dataset", ["admin_game_id"]
    )
    op.alter_column("memory_dataset", "source_kind", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    import living_memory.administration  # noqa: F401
    import living_memory.identity  # noqa: F401
    import living_memory.memory  # noqa: F401
    from living_memory.workspace import Base

    Base.metadata.drop_all(
        bind,
        tables=[
            table for table in reversed(Base.metadata.sorted_tables) if table.name.startswith("ws_")
        ],
    )
    op.drop_constraint("uq_memory_dataset_operational_game", "memory_dataset", type_="unique")
    op.drop_constraint("ck_memory_dataset_operational_owner", "memory_dataset", type_="check")
    op.drop_constraint("ck_memory_dataset_source_kind", "memory_dataset", type_="check")
    op.drop_constraint(
        "fk_memory_dataset_admin_game_id_admin_game", "memory_dataset", type_="foreignkey"
    )
    op.drop_column("memory_dataset", "admin_game_id")
    op.drop_column("memory_dataset", "source_kind")
