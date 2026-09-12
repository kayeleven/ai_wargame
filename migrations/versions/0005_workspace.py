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


# Explicit baseline DDL: never import application metadata in this migration.
# ruff: noqa: E501
def upgrade() -> None:
    _require_empty_0004()
    op.execute("""
CREATE TABLE ws_amendment (
	id UUID NOT NULL,
	submission_id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	base_version INTEGER NOT NULL,
	proposed_by UUID NOT NULL,
	version INTEGER NOT NULL,
	body JSONB NOT NULL,
	status VARCHAR NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_ws_amendment PRIMARY KEY (id),
	CONSTRAINT uq_ws_amendment_submission_id UNIQUE (submission_id, version),
	CONSTRAINT ck_ws_amendment_status CHECK (status IN ('pending','accepted','rejected'))
)
""")
    op.execute("""
CREATE TABLE ws_amendment_decision (
	id UUID NOT NULL,
	amendment_id UUID NOT NULL,
	decision VARCHAR NOT NULL,
	reason TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	adjudicator_user_id UUID NOT NULL,
	CONSTRAINT pk_ws_amendment_decision PRIMARY KEY (id),
	CONSTRAINT uq_ws_amendment_decision_amendment_id UNIQUE (amendment_id),
	CONSTRAINT ck_ws_amendment_decision_decision CHECK (decision IN ('accepted','rejected'))
)
""")
    op.execute("""
CREATE TABLE ws_coordination (
	id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	proposing_team_id VARCHAR NOT NULL,
	title VARCHAR NOT NULL,
	terms TEXT NOT NULL,
	status VARCHAR NOT NULL,
	version INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_ws_coordination PRIMARY KEY (id),
	CONSTRAINT uq_ws_coordination_id UNIQUE (id, game_id),
	CONSTRAINT ck_ws_coordination_status CHECK (status IN ('proposed','active','withdrawn'))
)
""")
    op.execute("""
CREATE TABLE ws_coordination_link (
	coordination_id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	action_id UUID NOT NULL,
	CONSTRAINT pk_ws_coordination_link PRIMARY KEY (coordination_id, game_id, team_id, action_id)
)
""")
    op.execute("""
CREATE TABLE ws_coordination_participant (
	coordination_id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_ws_coordination_participant PRIMARY KEY (coordination_id, game_id, team_id),
	CONSTRAINT ck_ws_coordination_participant_status CHECK (status IN ('pending','consented','declined','withdrawn'))
)
""")
    op.execute("""
CREATE TABLE ws_draft (
	id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	turn INTEGER NOT NULL,
	header JSONB NOT NULL,
	version INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_ws_draft PRIMARY KEY (id),
	CONSTRAINT uq_ws_draft_id UNIQUE (id, game_id, team_id),
	CONSTRAINT uq_ws_draft_game_id UNIQUE (game_id, team_id, turn)
)
""")
    op.execute("""
CREATE TABLE ws_draft_action (
	id UUID NOT NULL,
	draft_id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	action_id VARCHAR NOT NULL,
	owner_user_id UUID,
	position INTEGER NOT NULL,
	removed_at TIMESTAMP WITH TIME ZONE,
	origin VARCHAR NOT NULL,
	import_id UUID,
	body JSONB NOT NULL,
	version INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_ws_draft_action PRIMARY KEY (id),
	CONSTRAINT uq_ws_draft_action_id UNIQUE (id, game_id, team_id),
	CONSTRAINT uq_ws_draft_action_draft_id UNIQUE (draft_id, action_id),
	CONSTRAINT uq_ws_draft_action_draft_identity UNIQUE (id, draft_id),
	CONSTRAINT ck_ws_draft_action_origin CHECK (origin IN ('manual', 'import')),
	CONSTRAINT ck_ws_draft_action_version_nonnegative CHECK (version >= 0)
)
""")
    op.execute("""
CREATE TABLE ws_draft_comment (
	id UUID NOT NULL,
	draft_id UUID NOT NULL,
	draft_action_id UUID,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	author_user_id UUID NOT NULL,
	body TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	retracted_at TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_ws_draft_comment PRIMARY KEY (id)
)
""")
    op.execute("""
CREATE TABLE ws_draft_revision (
	id UUID NOT NULL,
	draft_action_id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	version INTEGER NOT NULL,
	body JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	author_user_id UUID,
	CONSTRAINT pk_ws_draft_revision PRIMARY KEY (id),
	CONSTRAINT uq_ws_draft_revision_draft_action_id UNIQUE (draft_action_id, version)
)
""")
    op.execute("""
CREATE TABLE ws_import (
	id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	action_id UUID,
	source_label VARCHAR NOT NULL,
	format VARCHAR NOT NULL,
	original_text TEXT NOT NULL,
	original_sha256 VARCHAR NOT NULL,
	mapping JSONB NOT NULL,
	missing_fields JSONB NOT NULL,
	missing_context JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_ws_import PRIMARY KEY (id),
	CONSTRAINT ck_ws_import_format CHECK (format = 'labeled-text-v1')
)
""")
    op.execute("""
CREATE TABLE ws_package_revision (
	id UUID NOT NULL,
	draft_id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	version INTEGER NOT NULL,
	snapshot JSONB NOT NULL,
	author_user_id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_ws_package_revision PRIMARY KEY (id),
	CONSTRAINT uq_ws_package_revision_draft_id UNIQUE (draft_id, version)
)
""")
    op.execute("""
CREATE TABLE ws_request_key (
	id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	branch_id VARCHAR NOT NULL,
	operation VARCHAR NOT NULL,
	key UUID NOT NULL,
	fingerprint VARCHAR NOT NULL,
	result_ref JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_ws_request_key PRIMARY KEY (id),
	CONSTRAINT uq_ws_request_key_game_id UNIQUE (game_id, branch_id, operation, key)
)
""")
    op.execute("""
CREATE TABLE ws_rfi (
	id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	title VARCHAR NOT NULL,
	type VARCHAR NOT NULL,
	question TEXT NOT NULL,
	recipient_role VARCHAR NOT NULL,
	visibility JSONB NOT NULL,
	status VARCHAR NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	withdrawn_at TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_ws_rfi PRIMARY KEY (id),
	CONSTRAINT uq_ws_rfi_id UNIQUE (id, game_id, team_id),
	CONSTRAINT ck_ws_rfi_status CHECK (status IN ('open','withdrawn'))
)
""")
    op.execute("""
CREATE TABLE ws_rfi_link (
	rfi_id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	action_id UUID NOT NULL,
	CONSTRAINT pk_ws_rfi_link PRIMARY KEY (rfi_id, game_id, team_id, action_id)
)
""")
    op.execute("""
CREATE TABLE ws_submission (
	id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	turn INTEGER NOT NULL,
	status VARCHAR NOT NULL,
	effective_version INTEGER NOT NULL,
	deadline TIMESTAMP WITH TIME ZONE NOT NULL,
	version INTEGER NOT NULL,
	submitted_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_ws_submission PRIMARY KEY (id),
	CONSTRAINT uq_ws_submission_id UNIQUE (id, game_id, team_id),
	CONSTRAINT uq_ws_submission_game_id UNIQUE (game_id, team_id, turn),
	CONSTRAINT ck_ws_submission_status CHECK (status IN ('submitted','amendment_pending'))
)
""")
    op.execute("""
CREATE TABLE ws_submission_version (
	id UUID NOT NULL,
	submission_id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	version INTEGER NOT NULL,
	snapshot JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	submitted_by UUID,
	CONSTRAINT pk_ws_submission_version PRIMARY KEY (id),
	CONSTRAINT uq_ws_submission_version_submission_id UNIQUE (submission_id, version)
)
""")
    op.execute("""
CREATE TABLE ws_submitted_action (
	id UUID NOT NULL,
	submission_id UUID NOT NULL,
	game_id VARCHAR NOT NULL,
	team_id VARCHAR NOT NULL,
	version INTEGER NOT NULL,
	action_id VARCHAR NOT NULL,
	body JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_ws_submitted_action PRIMARY KEY (id),
	CONSTRAINT uq_ws_submitted_action_submission_id UNIQUE (submission_id, version, action_id),
	CONSTRAINT uq_ws_submitted_action_id UNIQUE (id, game_id, team_id)
)
""")
    op.execute("""
ALTER TABLE ws_amendment ADD CONSTRAINT fk_ws_amendment_proposed_by_auth_user FOREIGN KEY(proposed_by) REFERENCES auth_user (id)
""")
    op.execute("""
ALTER TABLE ws_amendment ADD CONSTRAINT fk_ws_amendment_submission_id_ws_submission FOREIGN KEY(submission_id, game_id, team_id) REFERENCES ws_submission (id, game_id, team_id) ON DELETE RESTRICT
""")
    op.execute("""
ALTER TABLE ws_amendment_decision ADD CONSTRAINT fk_ws_amendment_decision_adjudicator_user_id_auth_user FOREIGN KEY(adjudicator_user_id) REFERENCES auth_user (id)
""")
    op.execute("""
ALTER TABLE ws_amendment_decision ADD CONSTRAINT fk_ws_amendment_decision_amendment_id_ws_amendment FOREIGN KEY(amendment_id) REFERENCES ws_amendment (id) ON DELETE RESTRICT
""")
    op.execute("""
ALTER TABLE ws_coordination ADD CONSTRAINT fk_ws_coordination_game_id_admin_team_state FOREIGN KEY(game_id, proposing_team_id) REFERENCES admin_team_state (game_id, team_id) ON DELETE RESTRICT
""")
    op.execute("""
ALTER TABLE ws_coordination_link ADD CONSTRAINT fk_ws_coordination_link_action_id_ws_submitted_action FOREIGN KEY(action_id, game_id, team_id) REFERENCES ws_submitted_action (id, game_id, team_id) ON DELETE RESTRICT
""")
    op.execute("""
ALTER TABLE ws_coordination_link ADD CONSTRAINT fk_ws_coordination_link_coordination_id_ws_coordination FOREIGN KEY(coordination_id, game_id) REFERENCES ws_coordination (id, game_id) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_coordination_participant ADD CONSTRAINT fk_ws_coordination_participant_coordination_id_ws_coordination FOREIGN KEY(coordination_id, game_id) REFERENCES ws_coordination (id, game_id) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_coordination_participant ADD CONSTRAINT fk_ws_coordination_participant_game_id_admin_team_state FOREIGN KEY(game_id, team_id) REFERENCES admin_team_state (game_id, team_id) ON DELETE RESTRICT
""")
    op.execute("""
ALTER TABLE ws_draft ADD CONSTRAINT fk_ws_draft_game_id_admin_team_state FOREIGN KEY(game_id, team_id) REFERENCES admin_team_state (game_id, team_id) ON DELETE RESTRICT
""")
    op.execute("""
ALTER TABLE ws_draft_action ADD CONSTRAINT fk_ws_draft_action_draft_id_ws_draft FOREIGN KEY(draft_id, game_id, team_id) REFERENCES ws_draft (id, game_id, team_id) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_draft_action ADD CONSTRAINT fk_ws_draft_action_import_id_ws_import FOREIGN KEY(import_id) REFERENCES ws_import (id) DEFERRABLE INITIALLY DEFERRED
""")
    op.execute("""
ALTER TABLE ws_draft_action ADD CONSTRAINT fk_ws_draft_action_owner_user_id_auth_user FOREIGN KEY(owner_user_id) REFERENCES auth_user (id)
""")
    op.execute("""
ALTER TABLE ws_draft_comment ADD CONSTRAINT fk_ws_comment_action_draft FOREIGN KEY(draft_action_id, draft_id) REFERENCES ws_draft_action (id, draft_id) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_draft_comment ADD CONSTRAINT fk_ws_draft_comment_author_user_id_auth_user FOREIGN KEY(author_user_id) REFERENCES auth_user (id)
""")
    op.execute("""
ALTER TABLE ws_draft_comment ADD CONSTRAINT fk_ws_draft_comment_draft_action_id_ws_draft_action FOREIGN KEY(draft_action_id, game_id, team_id) REFERENCES ws_draft_action (id, game_id, team_id) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_draft_comment ADD CONSTRAINT fk_ws_draft_comment_draft_id_ws_draft FOREIGN KEY(draft_id, game_id, team_id) REFERENCES ws_draft (id, game_id, team_id) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_draft_revision ADD CONSTRAINT fk_ws_draft_revision_author_user_id_auth_user FOREIGN KEY(author_user_id) REFERENCES auth_user (id)
""")
    op.execute("""
ALTER TABLE ws_draft_revision ADD CONSTRAINT fk_ws_draft_revision_draft_action_id_ws_draft_action FOREIGN KEY(draft_action_id, game_id, team_id) REFERENCES ws_draft_action (id, game_id, team_id) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_import ADD CONSTRAINT fk_ws_import_game_id_ws_draft_action FOREIGN KEY(game_id, team_id, action_id) REFERENCES ws_draft_action (game_id, team_id, id) DEFERRABLE INITIALLY DEFERRED
""")
    op.execute("""
ALTER TABLE ws_package_revision ADD CONSTRAINT fk_ws_package_revision_author_user_id_auth_user FOREIGN KEY(author_user_id) REFERENCES auth_user (id)
""")
    op.execute("""
ALTER TABLE ws_package_revision ADD CONSTRAINT fk_ws_package_revision_draft_id_ws_draft FOREIGN KEY(draft_id, game_id, team_id) REFERENCES ws_draft (id, game_id, team_id) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_request_key ADD CONSTRAINT fk_ws_request_key_game_id_admin_game FOREIGN KEY(game_id) REFERENCES admin_game (id) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_rfi ADD CONSTRAINT fk_ws_rfi_game_id_admin_team_state FOREIGN KEY(game_id, team_id) REFERENCES admin_team_state (game_id, team_id) ON DELETE RESTRICT
""")
    op.execute("""
ALTER TABLE ws_rfi_link ADD CONSTRAINT fk_ws_rfi_link_action_id_ws_submitted_action FOREIGN KEY(action_id, game_id, team_id) REFERENCES ws_submitted_action (id, game_id, team_id) ON DELETE RESTRICT
""")
    op.execute("""
ALTER TABLE ws_rfi_link ADD CONSTRAINT fk_ws_rfi_link_rfi_id_ws_rfi FOREIGN KEY(rfi_id, game_id, team_id) REFERENCES ws_rfi (id, game_id, team_id) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_submission ADD CONSTRAINT fk_ws_submission_effective_version FOREIGN KEY(id, effective_version) REFERENCES ws_submission_version (submission_id, version) DEFERRABLE INITIALLY DEFERRED
""")
    op.execute("""
ALTER TABLE ws_submission ADD CONSTRAINT fk_ws_submission_game_id_admin_team_state FOREIGN KEY(game_id, team_id) REFERENCES admin_team_state (game_id, team_id) ON DELETE RESTRICT
""")
    op.execute("""
ALTER TABLE ws_submission_version ADD CONSTRAINT fk_ws_submission_version_submission_id_ws_submission FOREIGN KEY(submission_id, game_id, team_id) REFERENCES ws_submission (id, game_id, team_id) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_submission_version ADD CONSTRAINT fk_ws_submission_version_submitted_by_auth_user FOREIGN KEY(submitted_by) REFERENCES auth_user (id)
""")
    op.execute("""
ALTER TABLE ws_submitted_action ADD CONSTRAINT fk_ws_submitted_action_content_version FOREIGN KEY(submission_id, version) REFERENCES ws_submission_version (submission_id, version) ON DELETE CASCADE
""")
    op.execute("""
ALTER TABLE ws_submitted_action ADD CONSTRAINT fk_ws_submitted_action_submission_id_ws_submission FOREIGN KEY(submission_id, game_id, team_id) REFERENCES ws_submission (id, game_id, team_id) ON DELETE CASCADE
""")
    op.execute("""
CREATE UNIQUE INDEX uq_ws_amendment_pending ON ws_amendment (submission_id) WHERE status = 'pending'
""")
    op.execute("""
CREATE UNIQUE INDEX uq_auth_team_submitter ON auth_team_membership (game_id, team_id) WHERE authority = 'submitter'
""")
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
    op.drop_index("uq_auth_team_submitter", table_name="auth_team_membership")
    op.drop_constraint("fk_ws_amendment_proposed_by_auth_user", "ws_amendment", type_="foreignkey")
    op.drop_constraint(
        "fk_ws_amendment_submission_id_ws_submission", "ws_amendment", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ws_amendment_decision_adjudicator_user_id_auth_user",
        "ws_amendment_decision",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_ws_amendment_decision_amendment_id_ws_amendment",
        "ws_amendment_decision",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_ws_coordination_game_id_admin_team_state", "ws_coordination", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ws_coordination_link_action_id_ws_submitted_action",
        "ws_coordination_link",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_ws_coordination_link_coordination_id_ws_coordination",
        "ws_coordination_link",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_ws_coordination_participant_coordination_id_ws_coordination",
        "ws_coordination_participant",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_ws_coordination_participant_game_id_admin_team_state",
        "ws_coordination_participant",
        type_="foreignkey",
    )
    op.drop_constraint("fk_ws_draft_game_id_admin_team_state", "ws_draft", type_="foreignkey")
    op.drop_constraint(
        "fk_ws_draft_action_draft_id_ws_draft", "ws_draft_action", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ws_draft_action_import_id_ws_import", "ws_draft_action", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ws_draft_action_owner_user_id_auth_user", "ws_draft_action", type_="foreignkey"
    )
    op.drop_constraint("fk_ws_comment_action_draft", "ws_draft_comment", type_="foreignkey")
    op.drop_constraint(
        "fk_ws_draft_comment_author_user_id_auth_user", "ws_draft_comment", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ws_draft_comment_draft_action_id_ws_draft_action",
        "ws_draft_comment",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_ws_draft_comment_draft_id_ws_draft", "ws_draft_comment", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ws_draft_revision_author_user_id_auth_user", "ws_draft_revision", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ws_draft_revision_draft_action_id_ws_draft_action",
        "ws_draft_revision",
        type_="foreignkey",
    )
    op.drop_constraint("fk_ws_import_game_id_ws_draft_action", "ws_import", type_="foreignkey")
    op.drop_constraint(
        "fk_ws_package_revision_author_user_id_auth_user", "ws_package_revision", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ws_package_revision_draft_id_ws_draft", "ws_package_revision", type_="foreignkey"
    )
    op.drop_constraint("fk_ws_request_key_game_id_admin_game", "ws_request_key", type_="foreignkey")
    op.drop_constraint("fk_ws_rfi_game_id_admin_team_state", "ws_rfi", type_="foreignkey")
    op.drop_constraint(
        "fk_ws_rfi_link_action_id_ws_submitted_action", "ws_rfi_link", type_="foreignkey"
    )
    op.drop_constraint("fk_ws_rfi_link_rfi_id_ws_rfi", "ws_rfi_link", type_="foreignkey")
    op.drop_constraint("fk_ws_submission_effective_version", "ws_submission", type_="foreignkey")
    op.drop_constraint(
        "fk_ws_submission_game_id_admin_team_state", "ws_submission", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ws_submission_version_submission_id_ws_submission",
        "ws_submission_version",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_ws_submission_version_submitted_by_auth_user",
        "ws_submission_version",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_ws_submitted_action_content_version", "ws_submitted_action", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ws_submitted_action_submission_id_ws_submission",
        "ws_submitted_action",
        type_="foreignkey",
    )
    op.drop_table("ws_submitted_action")
    op.drop_table("ws_submission_version")
    op.drop_table("ws_submission")
    op.drop_table("ws_rfi_link")
    op.drop_table("ws_rfi")
    op.drop_table("ws_request_key")
    op.drop_table("ws_package_revision")
    op.drop_table("ws_import")
    op.drop_table("ws_draft_revision")
    op.drop_table("ws_draft_comment")
    op.drop_table("ws_draft_action")
    op.drop_table("ws_draft")
    op.drop_table("ws_coordination_participant")
    op.drop_table("ws_coordination_link")
    op.drop_table("ws_coordination")
    op.drop_table("ws_amendment_decision")
    op.drop_table("ws_amendment")
    op.drop_constraint("uq_memory_dataset_operational_game", "memory_dataset", type_="unique")
    op.drop_constraint("ck_memory_dataset_operational_owner", "memory_dataset", type_="check")
    op.drop_constraint("ck_memory_dataset_source_kind", "memory_dataset", type_="check")
    op.drop_constraint(
        "fk_memory_dataset_admin_game_id_admin_game", "memory_dataset", type_="foreignkey"
    )
    op.drop_column("memory_dataset", "admin_game_id")
    op.drop_column("memory_dataset", "source_kind")
