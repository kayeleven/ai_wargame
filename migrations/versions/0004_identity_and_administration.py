"""Durable identity and game administration.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_user",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("pending", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "auth_local_credential",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("auth_user.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "auth_session",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.LargeBinary(32), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revocation_reason", sa.String()),
    )
    op.create_table(
        "auth_login_attempt",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("source_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_auth_login_attempt_username_time", "auth_login_attempt", ["username", "attempted_at"]
    )
    op.create_index(
        "ix_auth_login_attempt_source_time", "auth_login_attempt", ["source_hash", "attempted_at"]
    )
    op.create_table(
        "auth_global_role",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("auth_user.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(), primary_key=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("granted_by", sa.Uuid(), sa.ForeignKey("auth_user.id")),
        sa.CheckConstraint("role = 'system_admin'", name="ck_auth_global_role_role"),
    )
    op.create_table(
        "admin_game",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("public_rules", sa.String(), nullable=False),
        sa.Column("public_briefing", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("root_branch_id", sa.String(), nullable=False),
        sa.Column("current_turn", sa.Integer(), nullable=False),
        sa.Column("adjudicator_scopes", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'completed')", name="ck_admin_game_status"
        ),
    )
    op.create_table(
        "admin_configuration_revision",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "game_id",
            sa.String(),
            sa.ForeignKey("admin_game.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_turn", sa.Integer(), nullable=False),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
        sa.Column(
            "supersedes_revision_id", sa.Uuid(), sa.ForeignKey("admin_configuration_revision.id")
        ),
        sa.Column("author_user_id", sa.Uuid(), sa.ForeignKey("auth_user.id"), nullable=False),
        sa.UniqueConstraint("game_id", "sequence", name="uq_admin_configuration_revision_game_id"),
        sa.UniqueConstraint("id", "game_id", name="uq_admin_configuration_revision_id"),
    )
    op.create_table(
        "admin_team_state",
        sa.Column(
            "game_id",
            sa.String(),
            sa.ForeignKey("admin_game.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("team_id", sa.String(), primary_key=True),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "auth_game_role",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("auth_user.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "game_id",
            sa.String(),
            sa.ForeignKey("admin_game.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(), primary_key=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("granted_by", sa.Uuid(), sa.ForeignKey("auth_user.id")),
        sa.CheckConstraint("role IN ('game_admin', 'adjudicator')", name="ck_auth_game_role_role"),
    )
    op.create_table(
        "auth_team_membership",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("auth_user.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "game_id",
            sa.String(),
            sa.ForeignKey("admin_game.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("team_id", sa.String(), primary_key=True),
        sa.Column("authority", sa.String(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("granted_by", sa.Uuid(), sa.ForeignKey("auth_user.id")),
        sa.CheckConstraint(
            "authority IN ('member', 'submitter')", name="ck_auth_team_membership_authority"
        ),
    )
    op.create_table(
        "auth_provider_scope",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "game_id",
            sa.String(),
            sa.ForeignKey("admin_game.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("game_id", "provider", name="uq_auth_provider_scope_game_id"),
    )
    op.create_table(
        "auth_external_binding",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "provider_scope_id",
            sa.Uuid(),
            sa.ForeignKey("auth_provider_scope.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_subject", sa.String(), nullable=False),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("auth_user.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider_scope_id",
            "provider_subject",
            name="uq_auth_external_binding_provider_scope_id",
        ),
    )
    op.create_table(
        "auth_pending_access_request",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "binding_id",
            sa.Uuid(),
            sa.ForeignKey("auth_external_binding.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "game_id",
            sa.String(),
            sa.ForeignKey("admin_game.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("display_attributes", postgresql.JSONB(), nullable=False),
        sa.Column("observed_groups", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("auth_user.id")),
    )
    op.create_table(
        "auth_provider_group_mapping",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "provider_scope_id",
            sa.Uuid(),
            sa.ForeignKey("auth_provider_scope.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_group", sa.String(), nullable=False),
        sa.Column("suggested_team_id", sa.String()),
        sa.Column("suggested_role", sa.String()),
        sa.UniqueConstraint(
            "provider_scope_id",
            "external_group",
            name="uq_auth_provider_group_mapping_provider_scope_id",
        ),
    )
    op.create_table(
        "admin_alert",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "recipient_user_id",
            sa.Uuid(),
            sa.ForeignKey("auth_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("game_id", sa.String(), sa.ForeignKey("admin_game.id", ondelete="CASCADE")),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "admin_audit_entry",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("auth_user.id")),
        sa.Column("game_id", sa.String(), sa.ForeignKey("admin_game.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("subject_type", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "admin_audit_entry",
        "admin_alert",
        "auth_provider_group_mapping",
        "auth_pending_access_request",
        "auth_external_binding",
        "auth_provider_scope",
        "auth_team_membership",
        "auth_game_role",
        "admin_team_state",
        "admin_configuration_revision",
        "admin_game",
        "auth_global_role",
        "auth_login_attempt",
        "auth_session",
        "auth_local_credential",
        "auth_user",
    ):
        op.drop_table(table)
