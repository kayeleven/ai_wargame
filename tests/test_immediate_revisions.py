"""B-18 deadline policy, result-accurate recovery and archive integrity."""

# ruff: noqa: F811
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from test_admin_database import database  # noqa: F401
from test_effective_history import decide, rows
from test_recovery_corrections import target_factory  # noqa: F401
from test_workspace import GAME, NOW, ready, run, world  # noqa: F401
from test_workspace_command_hardening import ControlledClock, blocked_command, call
from test_workspace_web import ENHANCED, client_for, workspace_csrf

from living_memory import backup
from living_memory.administration import AdminGame
from living_memory.clocks import FixedClock
from living_memory.workspace import Amendment, EffectiveVersionEvent, Submission, SubmissionVersion
from living_memory.workspace_service import Command, ConfirmationRequired, confirmation_for

pytestmark = pytest.mark.integration
DEADLINE = NOW + timedelta(minutes=5)


def prepare(world):
    ready(world)
    run(world, "submit")
    with world[0].transaction() as s:
        s.scalars(select(Submission)).one().deadline = DEADLINE


def revision(world, at=NOW):
    with world[0].transaction() as s:
        sub = s.scalars(select(Submission)).one()
        from living_memory.workspace import Draft

        draft = s.scalars(select(Draft)).one()
        expected = confirmation_for(s, s.get(AdminGame, GAME), sub, 1, at)
        return Command(
            operation="amend", key=uuid4(), expected_version=draft.version, **expected.model_dump()
        )


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_deadline_policy_and_replay(world, offset):
    prepare(world)
    at = DEADLINE + timedelta(seconds=offset)
    cmd = revision(world, at)
    result = call(world, cmd, "player", FixedClock(at))
    immediate = offset < 0
    assert result["completion"]["expected_consequence"] == (
        "immediate" if immediate else "approval_required"
    )
    with world[0].transaction() as s:
        sub = s.scalars(select(Submission)).one()
        assert sub.effective_version == (2 if immediate else 1)
        assert sub.status == ("submitted" if immediate else "amendment_pending")
        assert len(s.scalars(select(Amendment)).all()) == (0 if immediate else 1)
        events = s.scalars(
            select(EffectiveVersionEvent).order_by(EffectiveVersionEvent.version)
        ).all()
        assert len(events) == (2 if immediate else 1)
        if immediate:
            assert events[-1].mechanism == "immediate_revision"
            assert events[-1].effective_at == at
            assert events[-1].responsible_user_id == world[2]["player"]
            assert events[-1].source_decision_id is None
    before = rows(world[0])
    assert call(world, cmd, "player", FixedClock(DEADLINE + timedelta(seconds=2))) == result
    assert rows(world[0]) == before


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_real_wait_deadline_policy(world, offset):
    prepare(world)
    cmd = revision(world)
    clock = ControlledClock(NOW)
    before = rows(world[0])

    def action(_):
        clock.advance(DEADLINE + timedelta(seconds=offset))

    if offset < 0:
        result = blocked_command(world, cmd, "player", clock, action)
        assert result["completion"]["expected_consequence"] == "immediate"
    else:
        with pytest.raises(ConfirmationRequired) as prompt:
            blocked_command(world, cmd, "player", clock, action)
        assert rows(world[0]) == before
        fresh = cmd.model_copy(update={"key": uuid4(), **prompt.value.expectations.model_dump()})
        result = call(world, fresh, "player", clock)
        assert result["completion"]["expected_consequence"] == "approval_required"


@pytest.mark.parametrize("immediate", [True, False])
@pytest.mark.parametrize("enhanced", [True, False])
def test_http_success_and_replay(world, immediate, enhanced):
    prepare(world)
    client = client_for(world)
    csrf = workspace_csrf(client)
    at = NOW if immediate else DEADLINE
    client.app.state.clock = FixedClock(at)
    cmd = revision(world, at)
    values = {
        **cmd.model_dump(
            mode="json",
            include={
                "operation",
                "key",
                "expected_version",
                "effective_version",
                "expected_deadline",
                "expected_consequence",
                "expected_late",
            },
        ),
        "csrf_token": csrf,
    }
    endpoint = f"/workspace/{GAME}/team-0/1/form"
    headers = ENHANCED if enhanced else {}
    response = client.post(endpoint, data=values, headers=headers, follow_redirects=False)
    expected = (
        "Revision is now effective." if immediate else "Amendment proposed for adjudicator review."
    )
    assert response.status_code == (200 if enhanced else 303)
    if enhanced:
        assert response.json()["message"] == expected
    else:
        assert expected in client.get(response.headers["location"]).text
    client.app.state.clock = FixedClock(DEADLINE + timedelta(seconds=1))
    before = rows(world[0])
    replay = client.post(endpoint, data=values, headers=headers, follow_redirects=False)
    assert replay.status_code == response.status_code
    if enhanced:
        assert replay.json() == response.json()
    else:
        assert replay.headers["location"] == response.headers["location"]
        assert expected in client.get(replay.headers["location"]).text
    after = rows(world[0])
    assert {k: v for k, v in after.items() if k != "auth_session"} == {
        k: v for k, v in before.items() if k != "auth_session"
    }


def test_immediate_rollback(world):
    prepare(world)
    cmd = revision(world)
    before = rows(world[0])
    from living_memory.workspace_service import execute

    with pytest.raises(RuntimeError), world[0].transaction() as s:
        execute(
            s,
            user_id=world[2]["player"],
            game_id=GAME,
            team_id="team-0",
            turn=1,
            command=cmd,
            clock=FixedClock(NOW),
        )
        raise RuntimeError("abort")
    assert rows(world[0]) == before


def test_rejected_then_immediate_and_restore(world, target_factory, tmp_path, monkeypatch):
    prepare(world)
    # Preserve a pre-policy pending proposal and its rejection before the deadline.
    with world[0].transaction() as s:
        s.scalars(select(Submission)).one().deadline = NOW
    run(world, "amend", effective_version=1)
    decide(world, "rejected")
    with world[0].transaction() as s:
        s.scalars(select(Submission)).one().deadline = DEADLINE
    cmd = revision(world)
    result = call(world, cmd, "player", FixedClock(NOW))
    with world[0].transaction() as s:
        assert list(
            s.scalars(select(SubmissionVersion.version).order_by(SubmissionVersion.version))
        ) == [1, 2, 3]
        assert list(
            s.scalars(select(EffectiveVersionEvent.version).order_by(EffectiveVersionEvent.version))
        ) == [1, 3]
    archive = tmp_path / "immediate.dump"
    backup.create_backup(world[0].engine.url.render_as_string(hide_password=False), archive)
    url, target, _ = target_factory()
    # Exact-version rejection precedes even opening the restore target.
    with monkeypatch.context() as patch:
        patch.setattr(backup, "APP_VERSION", "0.4.0")
        patch.setattr(backup, "_database_for_url", lambda _: pytest.fail("opened target"))
        with pytest.raises(ValueError, match="incompatible"):
            backup.restore_backup(url, archive)
    backup.restore_backup(url, archive)
    original, restored = rows(world[0]), rows(target)
    assert {k: v for k, v in original.items() if k != "admin_audit_entry"} == {
        k: v for k, v in restored.items() if k != "admin_audit_entry"
    }
    assert call((target, world[1], world[2]), cmd, "player", FixedClock(DEADLINE)) == result


@pytest.mark.parametrize("corruption", ["at_deadline", "after_deadline", "decision", "gap"])
def test_same_count_corruption_rejected(world, corruption, target_factory, tmp_path):
    prepare(world)
    call(world, revision(world), "player", FixedClock(NOW))
    db = world[0]
    with db.transaction() as s:
        backup._verify_effective_history(s)
    # Corrupt only the isolated test database, bypassing guards that normally
    # prohibit archive damage. Preserve row counts to exercise semantic checks.
    with db.engine.connect() as c:
        c.begin()
        c.execute(text("ALTER TABLE ws_effective_version_event DISABLE TRIGGER USER"))
        c.execute(text("ALTER TABLE ws_submission_version DISABLE TRIGGER USER"))
        if corruption in {"at_deadline", "after_deadline"}:
            at = DEADLINE + timedelta(seconds=corruption == "after_deadline")
            c.execute(
                text("UPDATE ws_effective_version_event SET effective_at=:at WHERE version=2"),
                {"at": at},
            )
            c.execute(
                text("UPDATE ws_submission_version SET created_at=:at WHERE version=2"), {"at": at}
            )
        elif corruption == "decision":
            c.execute(
                text(
                    "ALTER TABLE ws_effective_version_event "
                    "DROP CONSTRAINT ck_ws_effective_version_event_source"
                )
            )
            c.execute(
                text(
                    "ALTER TABLE ws_effective_version_event "
                    "DROP CONSTRAINT fk_ws_effective_event_decision"
                )
            )
            c.execute(
                text(
                    "UPDATE ws_effective_version_event SET source_decision_id=:id WHERE version=2"
                ),
                {"id": uuid4()},
            )
        else:
            # Make a gap without altering event provenance, so only contiguity fails.
            c.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            c.execute(
                text(
                    "ALTER TABLE ws_effective_version_event "
                    "DROP CONSTRAINT fk_ws_effective_event_content"
                )
            )
            c.execute(
                text("ALTER TABLE ws_submission DROP CONSTRAINT fk_ws_submission_effective_event")
            )
            c.execute(
                text(
                    "ALTER TABLE ws_submitted_action "
                    "DROP CONSTRAINT fk_ws_submitted_action_content_version"
                )
            )
            c.execute(text("UPDATE ws_submission_version SET version=3 WHERE version=2"))
            c.execute(text("UPDATE ws_effective_version_event SET version=3 WHERE version=2"))
            c.execute(text("UPDATE ws_submission SET effective_version=3"))
        c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        with Session(bind=c) as s, pytest.raises(ValueError, match="provenance"):
            backup._verify_effective_history(s)
        if corruption == "at_deadline":
            c.execute(text("ALTER TABLE ws_submission_version ENABLE TRIGGER USER"))
            c.execute(text("ALTER TABLE ws_effective_version_event ENABLE TRIGGER USER"))
            c.commit()
        # Other corruptions, including all schema changes, roll back on close.

    if corruption == "at_deadline":
        archive = tmp_path / "late-immediate.dump"
        backup.create_backup(db.engine.url.render_as_string(hide_password=False), archive)
        url, target, _ = target_factory()
        with pytest.raises(backup.RecoveryFailure):
            backup.restore_backup(url, archive)
        assert target.recovery_blocked() and not target.ready()


def test_concurrent_immediate_retries_share_completion(world):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    prepare(world)
    cmd = revision(world)
    barrier = Barrier(2)

    def submit():
        barrier.wait(timeout=5)
        return call(world, cmd, "player", FixedClock(NOW))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]
    assert results[0] == results[1]
    with world[0].transaction() as s:
        assert len(s.scalars(select(SubmissionVersion)).all()) == 2
        assert len(s.scalars(select(EffectiveVersionEvent)).all()) == 2


def test_legacy_pending_before_deadline_still_blocks_submission(world):
    from living_memory.workspace_service import Conflict

    ready(world)
    run(world, "submit")
    run(world, "amend", effective_version=1)
    with world[0].transaction() as s:
        s.scalars(select(Submission)).one().deadline = DEADLINE
    run(world, "intention", overall_intention="Edited while pending")
    cmd = revision(world)
    before = rows(world[0])
    with pytest.raises(Conflict):
        call(world, cmd, "player", FixedClock(NOW))
    assert rows(world[0]) == before
    decide(world, "accepted")
    with world[0].transaction() as s:
        event = s.scalars(
            select(EffectiveVersionEvent).where(EffectiveVersionEvent.version == 2)
        ).one()
        assert event.mechanism == "adjudicator_acceptance"
