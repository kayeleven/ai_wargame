"""Post-lock authority/time and authorized completion replay; no policy change."""
# ruff: noqa: F811

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from queue import Queue
from threading import Barrier, Lock
from time import monotonic, sleep
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from test_admin_database import database  # noqa: F401
from test_workspace import GAME, NOW, counts, ready, run, world  # noqa: F401

from living_memory.admin_access import replace_submitter
from living_memory.administration import AdminGame, lock_game
from living_memory.clocks import FixedClock
from living_memory.identity import GameRole, TeamMembership, User, deactivate_user
from living_memory.workspace import (
    Amendment,
    AmendmentDecision,
    EffectiveVersionEvent,
    IdempotencyConflict,
    RequestKey,
    SubmissionVersion,
)
from living_memory.workspace_service import Command, execute

pytestmark = pytest.mark.integration


@dataclass
class ControlledClock:
    instant: datetime = NOW
    lock: Lock = field(default_factory=Lock)

    def now(self):
        with self.lock:
            return self.instant

    def advance(self, instant):
        with self.lock:
            self.instant = instant


def prepared(world, operation):
    ready(world)
    cmd = Command(operation="submit", key=uuid4(), expected_version=2)
    if operation != "submit":
        run(world, "submit")
        cmd = Command(operation="amend", key=uuid4(), expected_version=3, effective_version=1)
    if operation == "decide":
        run(world, "amend", effective_version=1)
        with world[0].transaction() as s:
            amendment = s.scalars(select(Amendment)).one()
            cmd = Command(
                operation="decide",
                key=uuid4(),
                expected_version=2,
                amendment_id=amendment.id,
                decision="accepted",
                reason="Accept",
            )
    return cmd, "judge" if operation == "decide" else "player"


def call(world, cmd, who, clock):
    with world[0].transaction() as s:
        return execute(
            s,
            user_id=world[2][who],
            game_id=GAME,
            team_id="team-0",
            turn=1,
            command=cmd,
            clock=clock,
        )


def blocked_command(world, cmd, who, clock, while_blocked, table="admin_game"):
    """Prove a real PG lock wait, bounded both in SQL and in the harness."""
    db, _, ids = world
    pids = Queue()

    def worker():
        with db.transaction() as s:
            s.execute(text("SET LOCAL lock_timeout='3s'"))
            s.execute(text("SET LOCAL statement_timeout='4s'"))
            # Retain references: SQLAlchemy's identity map otherwise uses weak refs.
            cached = [
                s.get(User, ids[who]),
                s.get(AdminGame, GAME),
                s.get(TeamMembership, (ids[who], GAME, "team-0")),
                s.get(GameRole, (ids[who], GAME, "adjudicator")),
            ]
            pids.put(s.scalar(text("SELECT pg_backend_pid()")))
            result = execute(
                s,
                user_id=ids[who],
                game_id=GAME,
                team_id="team-0",
                turn=1,
                command=cmd,
                clock=clock,
            )
            assert cached[0] is not None
            return result

    pool = ThreadPoolExecutor(max_workers=1)
    try:
        with db.transaction() as blocker:
            blocker.execute(text("SET LOCAL lock_timeout='3s'"))
            blocker_pid = blocker.scalar(text("SELECT pg_backend_pid()"))
            if table == "admin_game":
                lock_game(blocker, GAME)
            else:
                blocker.execute(text(f"SELECT 1 FROM {table} FOR UPDATE"))
            future = pool.submit(worker)
            pid = pids.get(timeout=2)
            limit = monotonic() + 2
            while True:
                with db.engine.connect() as observer:
                    waiting = observer.scalar(
                        text("SELECT :blocker=ANY(pg_blocking_pids(:pid))"),
                        {"blocker": blocker_pid, "pid": pid},
                    )
                if waiting:
                    break
                assert monotonic() < limit, "worker did not enter the expected PostgreSQL lock wait"
                sleep(0.01)
            while_blocked(blocker)
        return future.result(timeout=5)
    finally:
        # SQL lock/statement timeouts bound worker completion even on assertion failure.
        pool.shutdown(wait=True, cancel_futures=True)


@pytest.mark.parametrize("operation", ["submit", "amend", "decide"])
def test_timestamp_is_read_after_real_lock_wait(world, operation):
    cmd, who = prepared(world, operation)
    db, _, _ = world
    deadline = NOW.replace(hour=0)
    clock = ControlledClock(deadline - timedelta(seconds=1))
    after = NOW + timedelta(seconds=1)
    result = blocked_command(world, cmd, who, clock, lambda _: clock.advance(after))
    with db.transaction() as s:
        record = s.scalar(select(RequestKey).where(RequestKey.key == cmd.key))
        assert record.created_at == after and record.result_ref == result
        if operation == "decide":
            assert s.get(AmendmentDecision, result["id"]).created_at == after
        else:
            version = 1 if operation == "submit" else 2
            assert (
                s.scalar(
                    select(SubmissionVersion).where(SubmissionVersion.version == version)
                ).created_at
                == after
            )
        if operation == "amend":
            assert s.scalars(select(Amendment)).one().status == "pending"
            assert len(s.scalars(select(EffectiveVersionEvent)).all()) == 1
        else:
            assert (
                s.scalars(
                    select(EffectiveVersionEvent).order_by(EffectiveVersionEvent.version.desc())
                )
                .first()
                .effective_at
                == after
            )


@pytest.mark.parametrize("table", ["auth_user", "ws_draft", "ws_submission", "ws_amendment"])
def test_clock_is_read_after_each_later_lock(world, table):
    cmd, who = prepared(world, "decide")
    clock = ControlledClock()
    after = NOW + timedelta(seconds=10)
    blocked_command(world, cmd, who, clock, lambda _: clock.advance(after), table=table)
    with world[0].transaction() as s:
        assert s.scalars(select(AmendmentDecision)).one().created_at == after


@pytest.mark.parametrize("revocation", ["membership", "submitter", "adjudicator", "inactive"])
@pytest.mark.parametrize("completed", [False, True])
def test_revoked_authority_during_wait_denies_even_cached_or_completed(
    world, revocation, completed
):
    cmd, who = prepared(world, "decide" if revocation == "adjudicator" else "submit")
    clock = ControlledClock()
    if completed:
        call(world, cmd, who, clock)
    before = counts(world[0])
    ids = world[2]

    def revoke(s):
        if revocation == "submitter":
            replace_submitter(s, ids["admin"], GAME, "team-0", ids["player"], ids["teammate"], NOW)
        elif revocation == "membership":
            s.delete(s.get(TeamMembership, (ids[who], GAME, "team-0")))
        elif revocation == "adjudicator":
            s.delete(s.get(GameRole, (ids[who], GAME, "adjudicator")))
        else:
            deactivate_user(s, ids[who], NOW, ids["admin"])
        clock.advance(NOW + timedelta(seconds=1))

    with pytest.raises(PermissionError if revocation == "submitter" else LookupError):
        blocked_command(world, cmd, who, clock, revoke)
    assert counts(world[0]) == before


@pytest.mark.parametrize("operation", ["submit", "amend", "decide"])
@pytest.mark.parametrize("later", ["edit", "advance", "complete"])
def test_completed_result_precedes_fresh_write_checks(world, operation, later):
    cmd, who = prepared(world, operation)
    expected = call(world, cmd, who, FixedClock(NOW))
    run(world, "intention", overall_intention="A later edit")
    if later != "edit":
        with world[0].transaction() as s:
            game = s.get(AdminGame, GAME)
            if later == "advance":
                game.current_turn = 2
            else:
                game.status = "completed"
    before = counts(world[0])
    assert call(world, cmd, who, FixedClock(NOW + timedelta(days=1))) == expected
    assert counts(world[0]) == before
    with pytest.raises(IdempotencyConflict):
        call(world, cmd.model_copy(update={"reason": "Different content"}), who, FixedClock(NOW))
    assert counts(world[0]) == before
    with pytest.raises(ValueError):
        call(world, cmd.model_copy(update={"key": uuid4()}), who, FixedClock(NOW))
    assert counts(world[0]) == before


@pytest.mark.parametrize("operation", ["submit", "amend", "decide"])
def test_concurrent_matching_commands_share_one_result(world, operation):
    cmd, who = prepared(world, operation)
    barrier = Barrier(2)

    def attempt():
        barrier.wait(timeout=3)
        return call(world, cmd, who, FixedClock(NOW))

    before = counts(world[0])
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        results = [future.result(timeout=6) for future in futures]
    assert results[0] == results[1]
    after = counts(world[0])
    assert after[3] == before[3] + 1  # One request key.
    assert after[-1] == before[-1] + (operation != "amend")
    assert after[5] == before[5] + (operation != "decide")
    assert after[8] == before[8] + (operation == "decide")
