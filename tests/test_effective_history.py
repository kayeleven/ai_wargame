"""Preserving 0006 upgrade, bounded aborts and durable event semantics."""
# ruff: noqa: F811

import importlib.util
from datetime import timedelta
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from test_admin_database import database  # noqa: F401
from test_recovery_corrections import target_factory  # noqa: F401
from test_workspace import GAME, NOW, confirmed_command, counts, ready, run, world  # noqa: F401

from living_memory import backup
from living_memory.clocks import FixedClock
from living_memory.db import ROOT, migration_config
from living_memory.workspace import Amendment, EffectiveVersionEvent, Submission
from living_memory.workspace_service import Command, execute

pytestmark = pytest.mark.integration


def decide(world, decision):
    db, _, _ = world
    with db.transaction() as s:
        a = s.scalars(select(Amendment).where(Amendment.status == "pending")).one()
        version = s.get(Submission, a.submission_id).version
    return run(
        world,
        "decide",
        version=version,
        who="judge",
        amendment_id=a.id,
        decision=decision,
        reason="A reason",
    )


def mixed_history(world):
    ready(world)
    run(world, "submit")
    run(world, "amend", effective_version=1)
    decide(world, "rejected")
    run(world, "amend", effective_version=1)
    decide(world, "accepted")
    run(world, "amend", effective_version=3)


def migrate(db, target="head", *, down=False):
    config = migration_config()
    with db.engine.begin() as connection:
        config.attributes["connection"] = connection
        (command.downgrade if down else command.upgrade)(config, target)


def rows(db):
    """Canonical full rows, including every old domain table, without emitting content."""
    with db.engine.connect() as c:
        names = c.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                "AND tablename<>'alembic_version' ORDER BY tablename"
            )
        ).scalars()
        return {
            name: c.execute(
                text(f'SELECT to_jsonb(t)::text FROM "{name}" t ORDER BY to_jsonb(t)::text')
            )
            .scalars()
            .all()
            for name in names
        }


@pytest.fixture
def legacy_history(world):
    db, _, ids = world
    mixed_history(world)
    # Construct the exact old schema on the dedicated test DB, retaining all old
    # rows. Do not use the intentionally forbidden populated production downgrade.
    with db.engine.begin() as c:
        c.execute(
            text("ALTER TABLE ws_submission DROP CONSTRAINT fk_ws_submission_effective_event")
        )
        c.execute(text("DROP TABLE ws_effective_version_event"))
        c.execute(text("DROP FUNCTION ws_effective_event_immutable()"))
        c.execute(text("UPDATE alembic_version SET version_num='0005'"))
        c.execute(text("UPDATE auth_user SET active=false WHERE id=:id"), {"id": ids["judge"]})
    yield world
    with db.engine.begin() as c:
        tables = (
            c.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename LIKE 'ws_%'"
                )
            )
            .scalars()
            .all()
        )
        c.execute(text("TRUNCATE " + ",".join(tables) + " CASCADE"))
    migrate(db)


def test_preserving_backfill_tied_times_inactive_actor_and_repeat(legacy_history):
    db, _, ids = legacy_history
    before = rows(db)
    migrate(db)
    after = rows(db)
    assert {k: after[k] for k in before} == before
    with db.transaction() as s:
        events = s.scalars(
            select(EffectiveVersionEvent).order_by(EffectiveVersionEvent.version)
        ).all()
        assert [
            (e.version, e.mechanism, e.responsible_user_id, e.effective_at) for e in events
        ] == [(1, "initial", ids["player"], NOW), (3, "adjudicator_acceptance", ids["judge"], NOW)]
        assert events[0].source_decision_id is None
        source = s.execute(
            text("SELECT id FROM ws_amendment_decision WHERE decision='accepted'")
        ).scalar_one()
        assert events[1].source_decision_id == source
    migrate(db)
    assert rows(db) == after
    with pytest.raises(ValueError, match="restore a pre-upgrade backup"):
        migrate(db, "0005", down=True)
    assert rows(db) == after


ABORTS = {
    "initial_provenance": "UPDATE ws_submission_version SET submitted_by=NULL WHERE version=1",
    "version_sequence": "DELETE FROM ws_submission_version WHERE version=2",
    "amendment_content": "UPDATE ws_amendment SET body='{}' WHERE version=2",
    "decision_consistency": "DELETE FROM ws_amendment_decision WHERE decision='rejected'",
    "decision_provenance": (
        "UPDATE ws_amendment_decision SET created_at=created_at-interval '1 second'"
    ),
    "effective_chain": "UPDATE ws_amendment SET base_version=2 WHERE version=4",
    "submission_state": "UPDATE ws_submission SET effective_version=1",
}


@pytest.mark.parametrize("invariant", ABORTS)
def test_each_invariant_aborts_without_changes(legacy_history, invariant):
    db, _, _ = legacy_history
    with db.engine.begin() as c:
        c.execute(text(ABORTS[invariant]))
    before = rows(db)
    with pytest.raises(ValueError, match=f"0006 {invariant}:") as error:
        migrate(db)
    assert len(str(error.value)) < 300
    assert rows(db) == before
    with db.engine.connect() as c:
        assert c.scalar(text("SELECT version_num FROM alembic_version")) == "0005"
        assert c.scalar(text("SELECT to_regclass('ws_effective_version_event')")) is None


def test_abort_cases_cover_every_named_check():
    spec = importlib.util.spec_from_file_location(
        "history_migration", ROOT / "migrations/versions/0006_effective_version_history.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert ABORTS.keys() == module.CHECKS.keys()


def test_events_replay_and_rollback(world):
    db, _, ids = world
    ready(world)
    key = uuid4()
    run(world, "submit", version=2, key=key)
    before = counts(db)
    run(world, "submit", version=2, key=key)
    assert counts(db) == before
    run(world, "amend", effective_version=1)
    with db.transaction() as s:
        a = s.scalars(select(Amendment)).one()
        version = s.get(Submission, a.submission_id).version
    cmd = Command(
        operation="decide",
        key=uuid4(),
        expected_version=version,
        amendment_id=a.id,
        decision="accepted",
        reason="Accept",
    )
    before = counts(db)
    with pytest.raises(RuntimeError, match="abort"), db.transaction() as s:
        execute(
            s,
            user_id=ids["judge"],
            game_id=GAME,
            team_id="team-0",
            turn=1,
            command=cmd,
            clock=FixedClock(NOW + timedelta(seconds=1)),
        )
        raise RuntimeError("abort")
    assert counts(db) == before
    with db.transaction() as s:
        result = execute(
            s,
            user_id=ids["judge"],
            game_id=GAME,
            team_id="team-0",
            turn=1,
            command=cmd,
            clock=FixedClock(NOW + timedelta(seconds=2)),
        )
    with db.transaction() as s:
        assert (
            execute(
                s,
                user_id=ids["judge"],
                game_id=GAME,
                team_id="team-0",
                turn=1,
                command=cmd,
                clock=FixedClock(NOW + timedelta(seconds=3)),
            )
            == result
        )
        events = s.scalars(
            select(EffectiveVersionEvent).order_by(EffectiveVersionEvent.version)
        ).all()
        assert len(events) == 2
        assert events[1].effective_at == NOW + timedelta(seconds=2)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE ws_effective_version_event SET effective_at=effective_at",
        "DELETE FROM ws_effective_version_event",
        "DELETE FROM ws_submission_version WHERE version=1",
        "DELETE FROM ws_submission",
        "DELETE FROM admin_game",
        "DELETE FROM auth_user WHERE id IN "
        "(SELECT responsible_user_id FROM ws_effective_version_event)",
    ],
)
def test_history_and_ancestors_cannot_be_deleted(world, statement):
    ready(world)
    run(world, "submit")
    db, _, _ = world
    before = rows(db)
    with pytest.raises(DBAPIError), db.engine.begin() as c:
        c.execute(text(statement))
    assert rows(db) == before


def test_effective_pointer_requires_event_at_commit(world):
    ready(world)
    run(world, "submit")
    run(world, "amend", effective_version=1)
    db, _, _ = world
    with pytest.raises(IntegrityError), db.engine.begin() as c:
        c.execute(text("UPDATE ws_submission SET effective_version=2"))
        # The statement succeeds; the deferred event FK must reject COMMIT.
        assert c.scalar(text("SELECT effective_version FROM ws_submission")) == 2


def corrupt_event_time(db):
    # Simulate a corrupt archive, not an application writer; re-enable the guard.
    with db.engine.begin() as c:
        c.execute(
            text(
                "ALTER TABLE ws_effective_version_event "
                "DISABLE TRIGGER ws_effective_event_immutable"
            )
        )
        c.execute(
            text(
                "UPDATE ws_effective_version_event "
                "SET effective_at=effective_at+interval '1 second'"
            )
        )
        c.execute(
            text(
                "ALTER TABLE ws_effective_version_event ENABLE TRIGGER ws_effective_event_immutable"
            )
        )


def test_restore_validation_detects_same_count_wrong_provenance(world):
    mixed_history(world)
    db, _, _ = world
    backup._verify_domain(db)
    corrupt_event_time(db)
    with pytest.raises(ValueError, match="provenance"):
        backup._verify_domain(db)


def test_migrated_history_backup_restore(legacy_history, target_factory, tmp_path):
    db, _, _ = legacy_history
    migrate(db)
    path = tmp_path / "history.dump"
    backup.create_backup(db.engine.url.render_as_string(hide_password=False), path)
    url, target, _ = target_factory()
    backup.restore_backup(url, path)
    original, restored = rows(db), rows(target)
    assert {k: v for k, v in restored.items() if k != "admin_audit_entry"} == {
        k: v for k, v in original.items() if k != "admin_audit_entry"
    }
    added = set(restored["admin_audit_entry"]) - set(original["admin_audit_entry"])
    assert len(added) == 1 and '"recovery_sessions_revoked"' in added.pop()
    assert set(original["admin_audit_entry"]) <= set(restored["admin_audit_entry"])
    assert backup._verify_domain(target)["counts"]["effective_version_events"] == 2
    with pytest.raises(DBAPIError, match="append-only"), target.engine.begin() as c:
        c.execute(text("DELETE FROM ws_effective_version_event"))


def test_corrupt_provenance_archive_leaves_restore_blocked(world, target_factory, tmp_path):
    mixed_history(world)
    db, _, _ = world
    corrupt_event_time(db)
    path = tmp_path / "corrupt.dump"
    backup.create_backup(db.engine.url.render_as_string(hide_password=False), path)
    url, target, _ = target_factory()
    with pytest.raises(backup.RecoveryFailure):
        backup.restore_backup(url, path)
    assert target.recovery_blocked() and not target.ready()


@pytest.mark.parametrize(
    "change",
    [
        "mechanism='unknown'",
        "mechanism='initial'",
        "source_decision_id=NULL",
        "responsible_user_id=NULL",
        "effective_at=NULL",
        "version=999",
    ],
)
def test_event_constraints(world, change):
    mixed_history(world)
    db, _, _ = world
    # Trigger must not mask the relational constraints being tested. Transaction
    # failure also rolls back this temporary disabling of the trigger.
    with pytest.raises(IntegrityError), db.engine.begin() as c:
        c.execute(
            text(
                "ALTER TABLE ws_effective_version_event "
                "DISABLE TRIGGER ws_effective_event_immutable"
            )
        )
        c.execute(text(f"UPDATE ws_effective_version_event SET {change} WHERE version=3"))


def test_initial_submission_rollback_leaves_no_event_or_command(world):
    db, _, ids = world
    ready(world)
    before = rows(db)
    cmd = confirmed_command(world, Command(operation="submit", key=uuid4(), expected_version=2))
    with pytest.raises(RuntimeError, match="abort"), db.transaction() as s:
        execute(
            s,
            user_id=ids["player"],
            game_id=GAME,
            team_id="team-0",
            turn=1,
            command=cmd,
            clock=FixedClock(NOW),
        )
        assert s.scalar(select(EffectiveVersionEvent)) is not None
        raise RuntimeError("abort")
    assert rows(db) == before
