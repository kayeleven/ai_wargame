"""Stage versioned development source packages; no game schema yet."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "development_artifact",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("package", sa.String(), nullable=False),
        sa.Column("package_version", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(), nullable=False),
        sa.Column("staged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contents", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_development_artifact"),
        sa.UniqueConstraint("package", "checksum", name="uq_development_artifact_package"),
    )


def downgrade():
    op.drop_table("development_artifact")
