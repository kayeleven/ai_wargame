"""Explicit confirmation, zero-write re-prompts and delayed-command safety."""
# ruff: noqa: F811

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, timezone
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_admin_database import database  # noqa: F401
from test_effective_history import rows
from test_workspace import (  # noqa: F401
    BODY,
    GAME,
    NOW,
    confirmed_command,
    counts,
    ready,
    run,
    world,
)
from test_workspace_command_hardening import ControlledClock, blocked_command, call, prepared
from test_workspace_web import ENHANCED, client_for, workspace_csrf

from living_memory.clocks import FixedClock
from living_memory.workspace import (
    DraftAction,
    RequestKey,
    SubmissionVersion,
    canonical_fingerprint,
)
from living_memory.workspace_service import (
    Command,
    Confirmation,
    ConfirmationRequired,
    Conflict,
    get_draft,
    package_at_version,
    submission_snapshot,
)
from living_memory.workspace_web import _confirmation_change_summary

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("operation", ["submit", "amend"])
@pytest.mark.parametrize(
    "field",
    ["missing", "effective_version", "expected_deadline", "expected_consequence", "expected_late"],
)
def test_missing_or_stale_confirmation_writes_nothing(world, operation, field):
    cmd, who = prepared(world, operation)
    changes = {
        "missing": dict(expected_deadline=None, expected_consequence=None, expected_late=None),
        "effective_version": dict(effective_version=99),
        "expected_deadline": dict(expected_deadline=NOW + timedelta(days=1)),
        "expected_consequence": dict(
            expected_consequence="immediate" if operation == "amend" else "approval_required"
        ),
        "expected_late": dict(expected_late=False),
    }
    before = rows(world[0])
    with pytest.raises(ConfirmationRequired):
        call(world, cmd.model_copy(update=changes[field]), who, FixedClock(NOW))
    assert rows(world[0]) == before


@pytest.mark.parametrize("operation", ["submit", "amend"])
def test_delayed_original_cannot_apply_after_fresh_confirmation(world, operation):
    original, who = prepared(world, operation)
    fresh = original.model_copy(update={"key": uuid4()})
    entered, release = Event(), Event()

    def delayed_original():
        entered.set()
        assert release.wait(timeout=5)
        return call(world, original, who, FixedClock(NOW))

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(delayed_original)
        try:
            assert entered.wait(timeout=2)
            before = counts(world[0])
            call(world, fresh, who, FixedClock(NOW))
            after = rows(world[0])
        finally:
            release.set()
        with pytest.raises((Conflict, ConfirmationRequired)):
            future.result(timeout=5)
    assert rows(world[0]) == after
    assert counts(world[0])[5] == before[5] + 1
    with world[0].transaction() as s:
        assert s.scalar(select(RequestKey).where(RequestKey.key == original.key)) is None


def test_clock_crossing_during_real_lock_wait_reprompts(world):
    ready(world)
    deadline = NOW.replace(hour=0)
    clock = ControlledClock(deadline - timedelta(seconds=1))
    cmd = confirmed_command(world, Command(operation="submit", key=uuid4(), expected_version=2))
    cmd = cmd.model_copy(update={"expected_late": False})
    before = rows(world[0])
    with pytest.raises(ConfirmationRequired):
        blocked_command(world, cmd, "player", clock, lambda _: clock.advance(NOW))
    assert rows(world[0]) == before


def test_legacy_completed_command_keeps_its_old_fingerprint(world):
    cmd, who = prepared(world, "submit")
    call(world, cmd, who, FixedClock(NOW))
    legacy = cmd.model_copy(
        update=dict(expected_deadline=None, expected_consequence=None, expected_late=None)
    )
    payload = legacy.model_dump(mode="json")
    for name in ("expected_deadline", "expected_consequence", "expected_late"):
        del payload[name]
    with world[0].transaction() as s:
        record = s.scalar(select(RequestKey).where(RequestKey.key == cmd.key))
        record.fingerprint = canonical_fingerprint(
            dict(user=str(world[2][who]), team="team-0", turn=1, command=payload)
        )
        result = {k: v for k, v in record.result_ref.items() if k != "completion"}
        record.result_ref = result
    assert call(world, legacy, who, FixedClock(NOW + timedelta(days=1))) == result


def test_http_confirmation_and_completion_replay(world):
    ready(world)
    client = client_for(world)
    values = dict(
        csrf_token=workspace_csrf(client), operation="submit", expected_version=2, key=str(uuid4())
    )
    endpoint = f"/workspace/{GAME}/team-0/1/form"
    before = counts(world[0])
    response = client.post(endpoint, data=values, headers=ENHANCED)
    assert response.status_code == 409
    prompt = response.json()
    assert prompt["outcome"] == "confirmation_required" and counts(world[0]) == before
    assert prompt["confirm"]["key"] != values["key"]
    values = {**prompt["confirm"], "csrf_token": values["csrf_token"]}
    confirmed = client.post(endpoint, data=values, headers=ENHANCED)
    assert confirmed.status_code == 200
    completion = confirmed.json()["completion"]
    assert completion["content_version"] == 1 and completion["expected_late"] is True
    assert completion["expected_consequence"] == "immediate"
    run(world, "intention", overall_intention="Later draft")
    assert client.post(endpoint, data=values, headers=ENHANCED).json() == confirmed.json()


def test_read_only_confirmation_does_not_claim_original_key(world):
    # Even multiple prompts on one unclaimed key need explicit fresh-key confirmation.
    cmd, who = prepared(world, "amend")
    cmd = cmd.model_copy(update={"expected_deadline": None})
    for _ in range(2):
        with pytest.raises(ConfirmationRequired):
            call(world, cmd, who, FixedClock(NOW))
    with world[0].transaction() as s:
        assert s.scalar(select(RequestKey).where(RequestKey.key == cmd.key)) is None


@pytest.mark.parametrize(
    ("current", "expected_changes"),
    [
        (
            dict(effective_version=2),
            ["The effective version changed from 1 to 2."],
        ),
        (
            dict(expected_deadline=NOW + timedelta(minutes=1)),
            ["The deadline changed from"],
        ),
        (
            dict(expected_consequence="approval_required"),
            ["The consequence changed from"],
        ),
        (
            dict(expected_late=True),
            ["The deadline passed while you were confirming."],
        ),
        (
            dict(
                effective_version=2,
                expected_deadline=NOW + timedelta(minutes=1),
                expected_consequence="approval_required",
                expected_late=True,
            ),
            [
                "The effective version changed from 1 to 2.",
                "The deadline changed from",
                "The consequence changed from",
                "The deadline status changed from",
            ],
        ),
    ],
)
def test_renewed_confirmation_lists_each_changed_expectation(current, expected_changes):
    command = Command(
        operation="amend",
        key=uuid4(),
        expected_version=7,
        effective_version=1,
        expected_deadline=NOW,
        expected_consequence="immediate",
        expected_late=False,
    )
    expectations = Confirmation(
        effective_version=current.get("effective_version", 1),
        expected_deadline=current.get("expected_deadline", NOW),
        expected_consequence=current.get("expected_consequence", "immediate"),
        expected_late=current.get("expected_late", False),
    )

    renewed, changes, announcement = _confirmation_change_summary(command, expectations)

    assert renewed
    assert len(changes) == len(expected_changes)
    for expected in expected_changes:
        assert any(change.startswith(expected) for change in changes)
    assert "Nothing was submitted by this attempt." in announcement
    assert "Confirming again is required." in announcement


def test_equivalent_timezone_deadline_is_not_described_as_a_change():
    command = Command(
        operation="amend",
        key=uuid4(),
        expected_version=7,
        effective_version=1,
        expected_deadline=NOW.astimezone(timezone(timedelta(hours=2))),
        expected_consequence="immediate",
        expected_late=False,
    )
    expectations = Confirmation(
        effective_version=1,
        expected_deadline=NOW,
        expected_consequence="approval_required",
        expected_late=False,
    )

    renewed, changes, announcement = _confirmation_change_summary(command, expectations)

    assert renewed and len(changes) == 1
    assert changes[0].startswith("The consequence changed from")
    assert "deadline changed" not in announcement


def test_initial_confirmation_is_not_described_as_a_renewal():
    command = Command(operation="submit", key=uuid4(), expected_version=2)
    expectations = Confirmation(
        effective_version=None,
        expected_deadline=NOW,
        expected_consequence="immediate",
        expected_late=True,
    )

    renewed, changes, announcement = _confirmation_change_summary(command, expectations)

    assert not renewed and changes == []
    assert "changed" not in announcement.lower()
    assert "again" not in announcement.lower()


def test_stale_confirmed_draft_is_not_silently_rebased(world):
    cmd, who = prepared(world, "submit")
    run(world, "intention", overall_intention="Changed after confirmation")
    before = rows(world[0])
    with pytest.raises(Conflict):
        call(world, cmd, who, FixedClock(NOW))
    assert rows(world[0]) == before


def test_submission_snapshot_excludes_removed_draft_action_from_exact_reviewed_revision(world):
    """The immutable expected draft revision uses the same live-action projection as commit."""
    ready(world)
    with world[0].transaction() as session:
        action_id = session.scalar(select(DraftAction.id))
    run(world, "remove", action_id=action_id)
    with world[0].transaction() as session:
        draft = get_draft(session, GAME, "team-0", 1)
        # The removal is revision 3; load the immutable source rather than live draft rows.
        reviewed = submission_snapshot(package_at_version(session, draft, 3))

    command = confirmed_command(world, Command(operation="submit", key=uuid4(), expected_version=3))
    call(world, command, "player", FixedClock(NOW))
    with world[0].transaction() as session:
        snapshot = session.scalar(select(SubmissionVersion.snapshot))
    assert snapshot == reviewed.model_dump(mode="json")
    assert len(snapshot["actions"]) == 0


def test_confirmation_reviewed_live_package_matches_committed_snapshot_with_removed_action(world):
    """The rendered review and commit share one immutable live-action draft projection."""
    ready(world)
    run(world, "action", body={**BODY, "title": "Second live action"})
    with world[0].transaction() as session:
        removed_action = session.scalars(
            select(DraftAction.id).order_by(DraftAction.position)
        ).first()
    run(world, "remove", action_id=removed_action)
    with world[0].transaction() as session:
        draft = get_draft(session, GAME, "team-0", 1)
        assert draft is not None
        expected_version = draft.version
        reviewed = submission_snapshot(package_at_version(session, draft, expected_version))

    client = client_for(world)
    csrf = workspace_csrf(client)
    endpoint = f"/workspace/{GAME}/team-0/1/form"
    original = {
        "csrf_token": csrf,
        "operation": "submit",
        "expected_version": expected_version,
        "key": str(uuid4()),
    }
    ordinary = client.post(endpoint, data=original)
    assert ordinary.status_code == 409
    assert ordinary.context["reviewed_package"].model_dump(mode="json") == reviewed.model_dump(
        mode="json"
    )

    prompt = client.post(endpoint, data={**original, "key": str(uuid4())}, headers=ENHANCED)
    assert prompt.status_code == 409
    payload = prompt.json()
    html = payload["html"]
    reviewed_start = html.index("data-reviewed-package")
    reviewed_end = html.index("<form", reviewed_start)
    reviewed_html = html[reviewed_start:reviewed_end]
    assert "Second live action" in reviewed_html
    assert BODY["title"] not in reviewed_html
    for value in (
        "Second live action",
        BODY["description"],
        BODY["intent"],
        BODY["anticipated_reaction"],
        "Unassigned",
    ):
        assert value in reviewed_html
    assert reviewed_html.index("Second live action") < reviewed_html.index(BODY["description"])

    committed = client.post(
        endpoint,
        data={**payload["confirm"], "csrf_token": csrf},
        headers=ENHANCED,
    )
    assert committed.status_code == 200
    with world[0].transaction() as session:
        snapshot = session.scalar(select(SubmissionVersion.snapshot))
    assert snapshot == reviewed.model_dump(mode="json")


def test_confirmation_review_keeps_immutable_prompt_snapshot_across_read_race(world, monkeypatch):
    """A draft edit after the prompt transaction rolls back cannot replace its review source."""
    from living_memory import workspace_web

    ready(world)
    client = client_for(world)
    csrf = workspace_csrf(client)
    endpoint = f"/workspace/{GAME}/team-0/1/form"
    original = {
        "csrf_token": csrf,
        "operation": "submit",
        "expected_version": 2,
        "key": str(uuid4()),
    }
    original_run_retryable = workspace_web.run_retryable
    edited = False

    def edit_after_confirmation_rollback(work):
        nonlocal edited
        try:
            return original_run_retryable(work)
        except ConfirmationRequired:
            if not edited:
                edited = True
                run(world, "intention", who="teammate", overall_intention="Later teammate draft")
            raise

    monkeypatch.setattr(workspace_web, "run_retryable", edit_after_confirmation_rollback)
    prompt = client.post(endpoint, data=original, headers=ENHANCED)
    assert prompt.status_code == 409 and edited
    payload = prompt.json()
    assert payload["confirm"]["expected_version"] == 2
    assert "A careful overall intention" in payload["html"]
    assert "Later teammate draft" not in payload["html"]

    confirmed = client.post(
        endpoint,
        data={**payload["confirm"], "csrf_token": csrf},
        headers=ENHANCED,
    )
    assert confirmed.status_code == 409 and confirmed.json()["outcome"] == "conflict"
    with world[0].transaction() as session:
        assert session.scalar(select(SubmissionVersion)) is None


def test_before_deadline_revision_is_immediate(world):
    cmd, who = prepared(world, "amend")
    before_deadline = NOW.replace(hour=0) - timedelta(seconds=1)
    with pytest.raises(ConfirmationRequired) as prompt:
        call(world, cmd, who, FixedClock(before_deadline))
    assert prompt.value.expectations.expected_consequence == "immediate"
    confirmed = cmd.model_copy(update=prompt.value.expectations.model_dump())
    result = call(world, confirmed, who, FixedClock(before_deadline))
    assert result["completion"]["expected_consequence"] == "immediate"
    assert result["completion"]["expected_late"] is False


def test_typed_json_confirmation_and_malformed_deadline(world):
    ready(world)
    client = client_for(world)
    endpoint = f"/workspace/{GAME}/team-0/1"
    headers = {"x-csrf-token": workspace_csrf(client)}
    values = dict(operation="submit", expected_version=2, key=str(uuid4()))
    before = rows(world[0])
    malformed = client.post(endpoint, json={**values, "expected_deadline": "tomorrow"},
                            headers=headers)
    assert malformed.status_code == 422
    prompt = client.post(endpoint, json=values, headers=headers)
    assert prompt.status_code == 409
    assert rows(world[0]) == before
    confirmed = client.post(endpoint, json=prompt.json()["confirm"], headers=headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["completion"]["content_version"] == 1


def test_ordinary_confirmation_renews_after_deadline_change(world):
    import re

    ready(world)
    client = client_for(world)
    client.app.state.clock = FixedClock(NOW.replace(hour=0) - timedelta(seconds=1))
    endpoint = f"/workspace/{GAME}/team-0/1/form"
    csrf = workspace_csrf(client)
    original = dict(operation="submit", expected_version=2, key=str(uuid4()), csrf_token=csrf)
    before = rows(world[0])
    prompt = client.post(endpoint, data=original)
    assert prompt.status_code == 409 and "Before the deadline." in prompt.text
    fields = dict(re.findall(r'name="([^"]+)" value="([^"]*)"', prompt.text))
    first_key = fields["key"]
    client.app.state.clock = FixedClock(NOW.replace(hour=0) + timedelta(seconds=1))
    renewed = client.post(endpoint, data=fields)
    assert renewed.status_code == 409 and "Late: the deadline" in renewed.text
    fields = dict(re.findall(r'name="([^"]+)" value="([^"]*)"', renewed.text))
    assert fields["key"] != first_key
    assert fields["expected_version"] == "2"
    after = rows(world[0])
    # Authentication refreshes last_seen_at independently of the workspace command.
    del before["auth_session"], after["auth_session"]
    assert after == before
    committed = client.post(endpoint, data=fields, follow_redirects=False)
    assert committed.status_code == 303
