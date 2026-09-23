"""Preserve and record the provenance of effective submission versions."""

from alembic import op
from sqlalchemy import text

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

# Each query returns only identifiers, never authored content. The LIMIT bounds
# diagnostics even on a large damaged history. Version order is authoritative;
# wall-clock timestamps can tie and are preserved, not used to invent ordering.
CHECKS = {
    "initial_provenance": """
        SELECT s.id FROM ws_submission s LEFT JOIN ws_submission_version v
          ON v.submission_id=s.id AND v.version=1
        WHERE v.id IS NULL OR v.submitted_by IS NULL OR v.created_at IS NULL
    """,
    "version_sequence": """
        SELECT submission_id FROM ws_submission_version GROUP BY submission_id
        HAVING min(version)<>1 OR max(version)<>count(*)
    """,
    "amendment_content": """
        SELECT coalesce(v.submission_id,a.submission_id) AS id
        FROM (SELECT * FROM ws_submission_version WHERE version<>1) v
        FULL JOIN ws_amendment a ON a.submission_id=v.submission_id AND a.version=v.version
        WHERE v.id IS NULL OR a.id IS NULL OR a.version<=1
          OR (v.game_id,v.team_id,v.snapshot,v.submitted_by,v.created_at)
             IS DISTINCT FROM (a.game_id,a.team_id,a.body,a.proposed_by,a.created_at)
    """,
    "decision_consistency": """
        SELECT a.id FROM ws_amendment a LEFT JOIN ws_amendment_decision d
          ON d.amendment_id=a.id
        WHERE (a.status='pending' AND d.id IS NOT NULL)
           OR (a.status<>'pending' AND (d.id IS NULL OR d.decision<>a.status))
    """,
    "decision_provenance": """
        SELECT d.id FROM ws_amendment_decision d JOIN ws_amendment a ON a.id=d.amendment_id
        WHERE d.adjudicator_user_id IS NULL OR d.created_at IS NULL
           OR d.created_at<a.created_at
    """,
    "effective_chain": """
        SELECT a.id FROM ws_amendment a
        WHERE a.base_version<>coalesce((SELECT max(p.version) FROM ws_amendment p
          WHERE p.submission_id=a.submission_id AND p.version<a.version
            AND p.status='accepted'),1)
          OR (a.status='pending' AND EXISTS (SELECT 1 FROM ws_amendment n
            WHERE n.submission_id=a.submission_id AND n.version>a.version))
    """,
    "submission_state": """
        SELECT s.id FROM ws_submission s
        WHERE s.effective_version<>coalesce((SELECT max(a.version) FROM ws_amendment a
          WHERE a.submission_id=s.id AND a.status='accepted'),1)
          OR (s.status='amendment_pending')<>EXISTS (SELECT 1 FROM ws_amendment a
            WHERE a.submission_id=s.id AND a.status='pending')
    """,
}


def upgrade() -> None:
    op.execute("""LOCK TABLE ws_submission, ws_submission_version, ws_amendment,
                  ws_amendment_decision, auth_user IN SHARE ROW EXCLUSIVE MODE""")
    for name, query in CHECKS.items():
        failures = op.get_bind().execute(text(f"SELECT * FROM ({query}) bad LIMIT 5")).all()
        if failures:
            ids = ", ".join(str(row[0]) for row in failures)
            raise ValueError(f"0006 {name}: history cannot support backfill; sample IDs: {ids}")
    op.execute("""
        CREATE TABLE ws_effective_version_event (
            submission_id UUID NOT NULL,
            version INTEGER NOT NULL,
            mechanism VARCHAR NOT NULL,
            responsible_user_id UUID NOT NULL,
            effective_at TIMESTAMP WITH TIME ZONE NOT NULL,
            source_decision_id UUID,
            CONSTRAINT pk_ws_effective_version_event PRIMARY KEY (submission_id, version),
            CONSTRAINT fk_ws_effective_event_content FOREIGN KEY (submission_id, version)
                REFERENCES ws_submission_version (submission_id, version) ON DELETE RESTRICT,
            CONSTRAINT fk_ws_effective_event_user FOREIGN KEY (responsible_user_id)
                REFERENCES auth_user (id) ON DELETE RESTRICT,
            CONSTRAINT fk_ws_effective_event_decision FOREIGN KEY (source_decision_id)
                REFERENCES ws_amendment_decision (id) ON DELETE RESTRICT,
            CONSTRAINT uq_ws_effective_event_decision UNIQUE (source_decision_id),
            CONSTRAINT ck_ws_effective_version_event_mechanism CHECK (
                mechanism IN ('initial','adjudicator_acceptance','immediate_revision')),
            CONSTRAINT ck_ws_effective_version_event_version CHECK (
                (mechanism='initial' AND version=1) OR (mechanism<>'initial' AND version>1)),
            CONSTRAINT ck_ws_effective_version_event_source CHECK (
                (mechanism='adjudicator_acceptance')=(source_decision_id IS NOT NULL))
        )
    """)
    op.execute("""
        INSERT INTO ws_effective_version_event
            (submission_id,version,mechanism,responsible_user_id,effective_at,source_decision_id)
        SELECT submission_id,version,'initial',submitted_by,created_at,NULL
        FROM ws_submission_version WHERE version=1
        UNION ALL
        SELECT a.submission_id,a.version,'adjudicator_acceptance',d.adjudicator_user_id,
               d.created_at,d.id
        FROM ws_amendment a JOIN ws_amendment_decision d ON d.amendment_id=a.id
        WHERE d.decision='accepted'
    """)
    op.execute("""
        ALTER TABLE ws_submission ADD CONSTRAINT fk_ws_submission_effective_event
        FOREIGN KEY (id,effective_version) REFERENCES ws_effective_version_event
        (submission_id,version) DEFERRABLE INITIALLY DEFERRED
    """)
    op.execute("""
        CREATE FUNCTION ws_effective_event_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'effective-version events are append-only';
        END $$
    """)
    op.execute("""
        CREATE TRIGGER ws_effective_event_immutable BEFORE UPDATE OR DELETE
        ON ws_effective_version_event FOR EACH ROW EXECUTE FUNCTION ws_effective_event_immutable()
    """)


def downgrade() -> None:
    op.execute("LOCK TABLE ws_effective_version_event IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(text("SELECT EXISTS (SELECT 1 FROM ws_effective_version_event)")):
        raise ValueError("0006 contains provenance; restore a pre-upgrade backup to roll back")
    op.drop_constraint("fk_ws_submission_effective_event", "ws_submission", type_="foreignkey")
    op.drop_table("ws_effective_version_event")
    op.execute("DROP FUNCTION ws_effective_event_immutable()")
