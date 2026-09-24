"""1D-1 service, authorization, concurrency, schema and recovery evidence."""

# ruff: noqa: F811
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from test_admin_database import config, database  # noqa: F401

from living_memory import backup
from living_memory.admin_access import replace_submitter, set_membership
from living_memory.administration import (
    AdminGame,
    AdministrationConflict,
    TeamOperationalState,
    activate_game,
    create_game,
)
from living_memory.clocks import FixedClock
from living_memory.db import Database
from living_memory.identity import GameRole, TeamMembership, create_local_user, deactivate_user
from living_memory.workspace import (
    Amendment,
    AmendmentDecision,
    Draft,
    DraftAction,
    DraftComment,
    EffectiveVersionEvent,
    IdempotencyConflict,
    PackageRevision,
    RequestKey,
    Submission,
    SubmissionVersion,
    SubmittedAction,
)
from living_memory.workspace_service import (
    Command,
    Conflict,
    confirmation_for,
    execute,
    get_draft,
    get_submission,
    package,
)

NOW = datetime(2040, 1, 1, 1, tzinfo=UTC)
START = datetime(2039, 1, 1, tzinfo=UTC)
GAME = "workspace-game"
BODY = dict(
    title="  Public initiative\n",
    description="Keep\n\nthis spacing.  ",
    intent="Seek cooperation",
    anticipated_reaction="They may decline",
)
pytestmark = pytest.mark.integration


@pytest.fixture
def world(database):
    db, settings = database
    with db.transaction() as session:
        users = {
            name: create_local_user(
                session, name, name.title(), "test password", START, system_admin=name == "admin"
            )
            for name in ("admin", "player", "teammate", "other", "judge")
        }
        game = create_game(session, GAME, "Workspace game", config(), users["admin"].id, START)
        for name, team, authority in (
            ("player", "team-0", "submitter"),
            ("teammate", "team-0", "member"),
            ("other", "team-1", "submitter"),
        ):
            session.add(
                TeamMembership(
                    user_id=users[name].id,
                    game_id=GAME,
                    team_id=team,
                    authority=authority,
                    granted_at=START,
                    granted_by=users["admin"].id,
                )
            )
        session.add(
            GameRole(
                user_id=users["judge"].id,
                game_id=GAME,
                role="adjudicator",
                granted_at=START,
                granted_by=users["admin"].id,
            )
        )
        session.flush()
        activate_game(session, game, users["admin"].id, START)
        ids = {name: user.id for name, user in users.items()}
    yield db, settings, ids
    with db.engine.begin() as connection:
        tables = (
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename LIKE 'ws_%' ORDER BY tablename"
                )
            )
            .scalars()
            .all()
        )
        connection.execute(text("TRUNCATE " + ",".join(tables) + " CASCADE"))


def confirmed_command(world, command, team="team-0"):
    """Explicitly construct a confirmed command for service fixture setup."""
    if command.operation not in {"submit", "amend"}:
        return command
    db, _, _ = world
    with db.transaction() as session:
        previous = session.scalar(select(RequestKey).where(RequestKey.key == command.key))
        expectations = previous.result_ref.get("completion") if previous else None
        if expectations is None:
            game = session.get(AdminGame, GAME)
            sub = get_submission(session, GAME, team, 1)
            expectations = confirmation_for(session, game, sub, 1, NOW).model_dump()
        fields = {k: expectations[k] for k in
                  ("expected_deadline", "expected_consequence", "expected_late")}
    return Command.model_validate({**command.model_dump(), **fields})


def run(world, operation, version=None, *, who="player", team="team-0", key=None, **values):
    db, _, ids = world
    if version is None:
        with db.transaction() as session:
            draft = get_draft(session, GAME, team, 1)
            version = draft.version if draft else 0
    command = Command(operation=operation, key=key or uuid4(), expected_version=version, **values)
    command = confirmed_command(world, command, team)
    with db.transaction() as session:
        return execute(
            session, user_id=ids[who], game_id=GAME, team_id=team, turn=1,
            command=command, clock=FixedClock(NOW)
        )


def ready(world):
    run(world, "intention", overall_intention="  A careful overall intention\n")
    run(world, "action", body=BODY, owner_user_id=world[2]["teammate"])


def counts(db):
    with db.transaction() as s:
        return tuple(
            s.scalar(select(func.count()).select_from(model))
            for model in (
                Draft,
                DraftAction,
                PackageRevision,
                RequestKey,
                Submission,
                SubmissionVersion,
                SubmittedAction,
                Amendment,
                AmendmentDecision,
                DraftComment,
                EffectiveVersionEvent,
            )
        )


def test_draft_history_submission_amendment(world):
    db, _, ids = world
    ready(world)
    with db.transaction() as s:
        action = s.scalar(select(DraftAction))
        aid = action.id
    run(world, "action", who="teammate", action_id=aid, body=BODY, owner_user_id=ids["player"])
    run(world, "comment", comment="Package discussion")
    run(world, "comment", who="teammate", action_id=aid, comment="Action discussion")
    run(world, "submit")
    with db.transaction() as s:
        sub = get_submission(s, GAME, "team-0", 1)
        assert sub.deadline < sub.submitted_at and sub.effective_version == 1
        original = s.scalar(select(SubmissionVersion)).snapshot
        assert original["actions"][0]["body"] == BODY
        assert original["overall_intention"] == "  A careful overall intention\n"
    run(world, "intention", overall_intention="Changed after submission")
    run(world, "amend", effective_version=1)
    with db.transaction() as s:
        sub = get_submission(s, GAME, "team-0", 1)
        amendment = s.scalar(select(Amendment))
        assert sub.effective_version == 1
        aid, version = amendment.id, sub.version
    run(
        world,
        "decide",
        version,
        who="judge",
        amendment_id=aid,
        decision="rejected",
        reason="Keep original",
    )
    with db.transaction() as s:
        assert get_submission(s, GAME, "team-0", 1).effective_version == 1
    run(world, "amend", effective_version=1)
    with db.transaction() as s:
        amendment = s.scalar(select(Amendment).where(Amendment.status == "pending"))
        aid, version = amendment.id, get_submission(s, GAME, "team-0", 1).version
    run(
        world,
        "decide",
        version,
        who="judge",
        amendment_id=aid,
        decision="accepted",
        reason="Agreed",
    )
    with db.transaction() as s:
        assert get_submission(s, GAME, "team-0", 1).effective_version == 3
        assert (
            s.scalar(select(SubmissionVersion).where(SubmissionVersion.version == 1)).snapshot
            == original
        )
        assert s.scalar(select(func.count()).select_from(SubmittedAction)) == 3


def test_conflict_preserves_base_and_rolls_back_everything(world):
    db, _, _ = world
    run(world, "intention", overall_intention="base")
    run(world, "intention", overall_intention="current")
    before = counts(db)
    with pytest.raises(Conflict) as error:
        run(world, "intention", 1, overall_intention="attempt")
    assert error.value.base["overall_intention"] == "base"
    assert error.value.current["overall_intention"] == "current"
    assert error.value.submitted["overall_intention"] == "attempt"
    assert counts(db) == before


def test_independent_editor_baselines_do_not_conflict(world):
    db, _, ids = world
    ready(world)
    with db.transaction() as session:
        action = session.scalar(select(DraftAction))
        assert action is not None
        action_id = action.id
    # Both editors started from revision 2. Saving intention must not invalidate
    # an action editor whose own scope is still unchanged.
    run(world, "intention", 2, overall_intention="Saved independently")
    run(
        world,
        "action",
        2,
        action_id=action_id,
        body={**BODY, "description": "My independent action edit"},
        owner_user_id=ids["teammate"],
    )
    with db.transaction() as session:
        assert package(session, get_draft(session, GAME, "team-0", 1)).actions[
            0
        ].body.description == "My independent action edit"

    # A stale editor for that same action still conflicts after a teammate edit.
    run(
        world,
        "action",
        4,
        who="teammate",
        action_id=action_id,
        body={**BODY, "description": "Teammate edit"},
        owner_user_id=ids["teammate"],
    )
    with pytest.raises(Conflict):
        run(
            world,
            "action",
            4,
            action_id=action_id,
            body={**BODY, "description": "Stale local edit"},
            owner_user_id=ids["teammate"],
        )


def test_validation_zero_actions_and_implicit_resubmit_rejected(world):
    db, _, _ = world
    before = counts(db)
    with pytest.raises(ValueError):
        run(world, "submit")
    assert counts(db) == before
    run(world, "intention", overall_intention="Observe only")
    run(world, "submit")
    before = counts(db)
    with pytest.raises(Conflict):
        run(world, "submit")
    assert counts(db) == before
    run(world, "action", body={"title": "Incomplete"})
    before = counts(db)
    with pytest.raises(ValueError):
        run(world, "amend", effective_version=1)
    assert counts(db) == before


def test_order_removal_and_history(world):
    db, _, _ = world
    ready(world)
    run(world, "action", body={**BODY, "title": "Second"})
    with db.transaction() as s:
        actions = package(s, get_draft(s, GAME, "team-0", 1)).actions
    run(world, "reorder", order=[actions[1].id, actions[0].id])
    run(world, "remove", action_id=actions[0].id)
    run(world, "submit")
    with db.transaction() as s:
        snap = s.scalar(select(SubmissionVersion)).snapshot
        assert [a["body"]["title"] for a in snap["actions"]] == ["Second"]
        assert len(package(s, get_draft(s, GAME, "team-0", 1)).actions) == 2
        assert s.scalar(select(PackageRevision).where(PackageRevision.version == 3)).snapshot[
            "actions"
        ][0]["id"] == str(actions[0].id)


def test_idempotency_and_revocation(world):
    db, _, ids = world
    key = uuid4()
    result = run(world, "intention", 0, key=key, overall_intention="original")
    before = counts(db)
    assert run(world, "intention", 0, key=key, overall_intention="original") == result
    assert counts(db) == before
    with pytest.raises(IdempotencyConflict):
        run(world, "intention", 0, key=key, overall_intention="different")
    with db.transaction() as s:
        deactivate_user(s, ids["player"], NOW, ids["admin"])
    with pytest.raises(LookupError):
        run(world, "intention", 0, key=key, overall_intention="original")
    assert counts(db) == before


@pytest.mark.parametrize("who", ["other", "admin", "judge"])
def test_private_commands_no_admin_bypass(world, who):
    before = counts(world[0])
    with pytest.raises(LookupError):
        run(world, "intention", who=who, overall_intention="Forbidden")
    assert counts(world[0]) == before


def test_member_cannot_submit_or_decide_and_foreign_action_is_hidden(world):
    ready(world)
    before = counts(world[0])
    with pytest.raises(PermissionError):
        run(world, "submit", who="teammate")
    with pytest.raises(LookupError):
        run(world, "action", action_id=uuid4(), body=BODY)
    with pytest.raises(LookupError):
        run(world, "decide", amendment_id=uuid4(), decision="accepted", reason="no")
    assert counts(world[0]) == before


def test_submitter_deactivate_replace_and_stale_replacement(world):
    db, _, ids = world
    with db.transaction() as s:
        deactivate_user(s, ids["player"], NOW, ids["admin"])
    with db.transaction() as s:
        assert s.get(TeamOperationalState, (GAME, "team-0")).blocked
        assert s.get(TeamMembership, (ids["player"], GAME, "team-0")).authority == "submitter"
    with pytest.raises(AdministrationConflict), db.transaction() as s:
        set_membership(
            s, ids["admin"], GAME, ids["teammate"], "team-0", "submitter", NOW, change=True
        )
    with pytest.raises(PermissionError), db.transaction() as s:
        replace_submitter(s, ids["teammate"], GAME, "team-0", ids["player"], ids["teammate"], NOW)
    with db.transaction() as s:
        replace_submitter(s, ids["admin"], GAME, "team-0", ids["player"], ids["teammate"], NOW)
    with db.transaction() as s:
        assert not s.get(TeamOperationalState, (GAME, "team-0")).blocked
    run(world, "intention", who="teammate", overall_intention="New submitter")
    run(world, "submit", who="teammate")
    with pytest.raises(AdministrationConflict), db.transaction() as s:
        replace_submitter(s, ids["admin"], GAME, "team-0", ids["player"], ids["teammate"], NOW)


@pytest.mark.parametrize(
    "scenario",
    ["edits", "duplicate", "submits", "edit_submit", "decisions", "replacement", "revocation"],
)
def test_concurrent_mutations_are_atomic(world, scenario):
    db, _, ids = world
    ready(world)
    version = 2
    barrier = Barrier(2)
    key = uuid4()
    if scenario == "decisions":
        run(world, "submit")
        run(world, "amend", effective_version=1)
        with db.transaction() as s:
            amendment_id = s.scalar(select(Amendment.id))
            version = get_submission(s, GAME, "team-0", 1).version
    before = counts(db)

    def work(index):
        barrier.wait(timeout=5)
        try:
            if scenario == "replacement":
                with db.transaction() as s:
                    replace_submitter(
                        s, ids["admin"], GAME, "team-0", ids["player"], ids["teammate"], NOW
                    )
            elif scenario == "revocation" and index == 0:
                with db.transaction() as s:
                    deactivate_user(s, ids["player"], NOW, ids["admin"])
            elif scenario == "decisions":
                run(
                    world,
                    "decide",
                    version,
                    who="judge",
                    amendment_id=amendment_id,
                    decision="accepted" if index else "rejected",
                    reason="Decision",
                )
            elif scenario in {"submits", "edit_submit"} and (scenario == "submits" or index == 0):
                run(world, "submit", version)
            else:
                run(
                    world,
                    "intention",
                    version,
                    key=key if scenario == "duplicate" else None,
                    overall_intention="Concurrent" if scenario == "duplicate" else str(index),
                )
            return "ok"
        except (Conflict, AdministrationConflict, LookupError):
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(work, (0, 1)))
    after = counts(db)
    if scenario in {"edits", "submits", "decisions", "replacement"}:
        assert sorted(outcomes) == ["conflict", "ok"]
    if scenario == "edit_submit":
        # If the aggregate submission wins the lock it freezes the original package,
        # then the scoped intention edit may validly commit against its unchanged scope.
        # If the edit wins first, the stale aggregate submission conflicts.
        assert sorted(outcomes) in (["conflict", "ok"], ["ok", "ok"])
    if scenario == "duplicate":
        assert outcomes == ["ok", "ok"]
    if scenario not in {"replacement", "revocation"}:
        expected_commits = outcomes.count("ok") if scenario == "edit_submit" else 1
        assert after[3] == before[3] + expected_commits  # no failed request-key residue
        assert after[2] == before[2] + (0 if scenario == "decisions" else expected_commits)
    if scenario in {"submits", "edit_submit"}:
        with db.transaction() as s:
            versions = s.scalars(select(SubmissionVersion)).all()
            if versions:
                assert (
                    versions[0].snapshot["overall_intention"] == "  A careful overall intention\n"
                )
    if scenario in {"submits", "edit_submit", "decisions"}:
        backup._verify_domain(db)  # Concurrent winners have exactly their source-derived events.
    if scenario == "decisions":
        assert after[8] == before[8] + 1


def test_schema_constraints_and_retained_tables(world):
    db, _, ids = world
    with db.transaction() as s:
        for table in (
            "ws_import",
            "ws_coordination",
            "ws_coordination_participant",
            "ws_coordination_link",
            "ws_rfi",
            "ws_rfi_link",
        ):
            assert s.scalar(text(f"SELECT count(*) FROM {table}")) == 0
        constraints = s.execute(
            text(
                "SELECT conname, condeferrable, condeferred FROM pg_constraint "
                "WHERE conrelid IN ('ws_import'::regclass, 'ws_draft_action'::regclass) "
                "AND contype='f'"
            )
        ).all()
        assert any("import_id" in r[0] and r[1] and r[2] for r in constraints)
        assert any("game_id" in r[0] and r[1] and r[2] for r in constraints)
    with pytest.raises(IntegrityError), db.transaction() as s:
        s.get(TeamMembership, (ids["teammate"], GAME, "team-0")).authority = "submitter"
    ready(world)
    run(world, "submit")
    run(world, "amend", effective_version=1)
    with pytest.raises(IntegrityError), db.transaction() as s:
        a = s.scalar(select(Amendment))
        s.add(
            Amendment(
                submission_id=a.submission_id,
                game_id=GAME,
                team_id="team-0",
                version=99,
                base_version=1,
                proposed_by=ids["player"],
                body=a.body,
                status="pending",
                created_at=NOW,
            )
        )
    with pytest.raises(IntegrityError), db.transaction() as s:
        a = s.scalar(select(SubmittedAction).limit(1))
        s.add(
            SubmittedAction(
                submission_id=a.submission_id,
                game_id=GAME,
                team_id="team-0",
                version=a.version,
                action_id=a.action_id,
                body=a.body,
                created_at=NOW,
            )
        )


def test_backup_same_head_old_version_rejected_and_roundtrip(world, tmp_path, monkeypatch):
    db, settings, _ = world
    ready(world)
    run(world, "comment", comment="Retain discussion")
    run(world, "submit")
    run(world, "amend", effective_version=1)
    path = tmp_path / "workspace.dump"
    backup.create_backup(db.engine.url.render_as_string(hide_password=False), path)
    manifest = backup.verify_backup(path)
    assert manifest.application_version == "0.4.0" and manifest.schema_heads == ["0006"]
    sidecar = path.with_suffix(".dump.json")
    original = sidecar.read_text()
    old = json.loads(original)
    old["application_version"] = "0.2.0"
    sidecar.write_text(json.dumps(old))
    with monkeypatch.context() as patch:
        patch.setattr(backup, "_run", lambda *a, **k: pytest.fail("Restore must not run"))
        with pytest.raises(ValueError, match="incompatible"):
            backup.restore_backup(
                db.engine.url.set(database="never_restore").render_as_string(hide_password=False),
                path,
            )
    sidecar.write_text(original)
    name = "lm_workspace_" + uuid4().hex
    subprocess.run(
        [
            "docker",
            "exec",
            "living_memory-db-1",
            "createdb",
            "-U",
            "living_memory",
            "-T",
            "template0",
            "-O",
            "living_memory_test",
            name,
        ],
        check=True,
    )
    target = Database(
        settings.model_copy(
            update={
                "database_url": SecretStr(
                    db.engine.url.set(database=name).render_as_string(hide_password=False)
                )
            }
        )
    )
    try:
        backup.restore_backup(target.engine.url.render_as_string(hide_password=False), path)
        assert counts(target) == counts(db)
        with target.transaction() as s:
            inventory = backup._domain_inventory_session(s)
            assert inventory["counts"]["submissions"] == 1
            assert inventory["counts"]["coordination_participants"] == 0
    finally:
        target.close()
        subprocess.run(
            ["docker", "exec", "living_memory-db-1", "dropdb", "-U", "living_memory", name],
            check=True,
        )


def test_foreign_action_and_replay_reauthorization(world):
    db, _, _ = world
    ready(world)
    run(world, "action", who="other", team="team-1", body={**BODY, "title": "Private other action"})
    with db.transaction() as s:
        foreign = s.scalar(select(DraftAction.id).where(DraftAction.team_id == "team-1"))
    before = counts(db)
    for aid in (foreign, uuid4()):
        with pytest.raises(LookupError, match="Not found"):
            run(world, "comment", action_id=aid, comment="Cannot link private action")
    assert counts(db) == before
    key = uuid4()
    result = run(world, "submit", 2, key=key)
    with db.transaction() as s:
        assert s.get(PackageRevision, result["id"]) is not None
        replace_submitter(
            s, world[2]["admin"], GAME, "team-0", world[2]["player"], world[2]["teammate"], NOW
        )
    before = counts(db)
    with pytest.raises(PermissionError):
        run(world, "submit", 2, key=key)
    assert counts(db) == before


def test_completed_action_command_replays_after_target_is_removed(world):
    db, _, ids = world
    ready(world)
    with db.transaction() as session:
        action_id = session.scalar(select(DraftAction.id).where(DraftAction.team_id == "team-0"))
        assert action_id is not None

    key = uuid4()
    result = run(
        world,
        "action",
        key=key,
        action_id=action_id,
        body={**BODY, "description": "Saved before removal"},
        owner_user_id=ids["teammate"],
    )
    run(world, "remove", action_id=action_id)
    before = counts(db)

    replay = run(
        world,
        "action",
        2,
        key=key,
        action_id=action_id,
        body={**BODY, "description": "Saved before removal"},
        owner_user_id=ids["teammate"],
    )

    assert replay == result
    assert counts(db) == before


def test_retained_import_cycle_flushes_and_remains_outside_workflow(world):
    from living_memory.workspace import WorkspaceImport, canonical_fingerprint

    db, _, _ = world
    ready(world)
    with db.transaction() as s:
        draft = get_draft(s, GAME, "team-0", 1)
        aid, iid = uuid4(), uuid4()
        s.add(
            DraftAction(
                id=aid,
                draft_id=draft.id,
                game_id=GAME,
                team_id="team-0",
                action_id=str(aid),
                origin="import",
                import_id=iid,
                body={},
                version=0,
                position=1,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        s.flush()  # import target deliberately not yet present
        s.add(
            WorkspaceImport(
                id=iid,
                game_id=GAME,
                team_id="team-0",
                action_id=aid,
                source_label="test only",
                format="labeled-text-v1",
                original_text="Title: Example",
                original_sha256=canonical_fingerprint("Title: Example"),
                mapping={},
                missing_fields=[],
                missing_context=[],
                created_at=NOW,
            )
        )
        s.flush()


def test_inactive_noncurrent_mutations_and_replays_leave_no_writes(world):
    from living_memory.administration import AdminGame

    db, _, _ = world
    key = uuid4()
    run(world, "intention", 0, key=key, overall_intention="Original")
    before = counts(db)
    for status, turn in (("draft", 1), ("completed", 1), ("active", 2)):
        with db.transaction() as s:
            game = s.get(AdminGame, GAME)
            game.status, game.current_turn = status, turn
        for operation, version, request_key in (
            ("intention", 0, key),
            ("intention", 1, uuid4()),
            ("submit", 1, uuid4()),
        ):
            with pytest.raises(ValueError, match="active current turn"):
                run(world, operation, version, key=request_key, overall_intention="Original")
            assert counts(db) == before


def test_deadline_snapshot_survives_a_later_governing_configuration(world):
    from datetime import timedelta

    from living_memory.administration import ConfigurationRevision

    db, _, ids = world
    ready(world)
    run(world, "submit")
    with db.transaction() as s:
        sub = get_submission(s, GAME, "team-0", 1)
        original_deadline = sub.deadline
        previous = s.scalar(
            select(ConfigurationRevision).where(ConfigurationRevision.game_id == GAME)
        )
        revised = config().model_dump(mode="json")
        revised["turns"][0]["submission_deadline"] = (NOW + timedelta(minutes=30)).isoformat()
        # Simulate a later authoritative configuration revision. Existing 1C admin
        # does not offer current-turn revision; the snapshot must remain independent.
        s.add(
            ConfigurationRevision(
                game_id=GAME,
                sequence=previous.sequence + 1,
                effective_turn=1,
                recorded_at=NOW,
                configuration=revised,
                supersedes_revision_id=previous.id,
                author_user_id=ids["admin"],
            )
        )
    run(world, "amend", effective_version=1)
    with db.transaction() as s:
        sub = get_submission(s, GAME, "team-0", 1)
        assert sub.deadline == original_deadline
        assert sub.submitted_at > sub.deadline


def review_history(world):
    """Real rejected history followed by one pending amendment, for web/browser checks."""
    ready(world)
    run(world, "submit")
    run(world, "intention", overall_intention="Rejected proposal")
    run(world, "amend", effective_version=1)
    with world[0].transaction() as session:
        rejected = session.scalar(select(Amendment))
        rejected_id = rejected.id
        version = get_submission(session, GAME, "team-0", 1).version
    run(
        world,
        "decide",
        version,
        who="judge",
        amendment_id=rejected_id,
        decision="rejected",
        reason="Preserved rejection reason",
    )
    run(world, "intention", overall_intention="Pending proposal")
    run(world, "amend", effective_version=1)
    with world[0].transaction() as session:
        pending_id = session.scalar(select(Amendment.id).where(Amendment.status == "pending"))
    return rejected_id, pending_id
