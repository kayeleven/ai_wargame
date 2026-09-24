"""Explicit confirmation, zero-write re-prompts and delayed-command safety."""
# ruff: noqa: F811

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_admin_database import database  # noqa: F401
from test_effective_history import rows
from test_workspace import GAME, NOW, confirmed_command, counts, ready, run, world  # noqa: F401
from test_workspace_command_hardening import ControlledClock, blocked_command, call, prepared
from test_workspace_web import ENHANCED, client_for, workspace_csrf

from living_memory.clocks import FixedClock
from living_memory.workspace import RequestKey, canonical_fingerprint
from living_memory.workspace_service import Command, ConfirmationRequired, Conflict

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


def test_stale_confirmed_draft_is_not_silently_rebased(world):
    cmd, who = prepared(world, "submit")
    run(world, "intention", overall_intention="Changed after confirmation")
    before = rows(world[0])
    with pytest.raises(Conflict):
        call(world, cmd, who, FixedClock(NOW))
    assert rows(world[0]) == before


def test_before_deadline_revision_still_requires_acceptance(world):
    cmd, who = prepared(world, "amend")
    before_deadline = NOW.replace(hour=0) - timedelta(seconds=1)
    with pytest.raises(ConfirmationRequired) as prompt:
        call(world, cmd, who, FixedClock(before_deadline))
    assert prompt.value.expectations.expected_consequence == "approval_required"
    confirmed = cmd.model_copy(update=prompt.value.expectations.model_dump())
    result = call(world, confirmed, who, FixedClock(before_deadline))
    assert result["completion"]["expected_consequence"] == "approval_required"
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
