# ruff: noqa: F811
import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_admin_database import database  # noqa: F401
from test_workspace import BODY, GAME, NOW, ready, run, world  # noqa: F401

from living_memory.app import create_app
from living_memory.clocks import FixedClock
from living_memory.identity import issue_session
from living_memory.workspace import Amendment, DraftAction

pytestmark = pytest.mark.integration

ENHANCED = {
    "Accept": "application/vnd.living-memory.workspace+json",
    "X-Workspace-Enhanced": "1",
}


def client_for(world, who="player"):
    db, settings, ids = world
    with db.transaction() as session:
        token = issue_session(session, ids[who], NOW)
    client = TestClient(create_app(settings, db, FixedClock(NOW)))
    client.cookies.set("lm_auth", token)
    return client


def workspace_csrf(client):
    page = client.get(f"/play?game_id={GAME}")
    return re.search(r'name="csrf_token" value="([^"]+)"', page.text)[1]


def test_workspace_routes_authorized_and_split(world):
    ready(world)
    client = client_for(world)
    response = client.get(f"/play?game_id={GAME}")
    assert response.status_code == 200
    assert "Shared draft" in response.text and "Public initiative" in response.text
    for forbidden in ("Coordination", "Submit RFI", "Import", "labeled-text"):
        assert forbidden not in response.text
    assert response.headers["Cache-Control"] == "no-store"
    assert client.get(f"/play?game_id={GAME}&team_id=team-1").status_code == 404
    assert (
        client.get(f"/play?game_id={GAME}&team_id=unknown").json()
        == client.get(f"/play?game_id={GAME}&team_id=team-1").json()
    )
    assert client.get(f"/adjudicate?game_id={GAME}").status_code == 404
    admin = client_for(world, "admin")
    assert admin.get(f"/play?game_id={GAME}").status_code == 404
    judge = client_for(world, "judge")
    assert judge.get(f"/adjudicate?game_id={GAME}").status_code == 200


def test_home_exposes_only_authorized_tasks_and_shared_account_controls(world):
    player = client_for(world)
    home = player.get("/")
    assert home.status_code == 200
    assert f'/play?game_id={GAME}&team_id=team-0' in home.text
    assert "Team 0 workspace · submitter" in home.text
    assert "Amendment review" not in home.text
    assert "Game administration" not in home.text
    assert 'action="/logout"' in home.text

    judge = client_for(world, "judge")
    judge_home = judge.get("/")
    assert "Amendment review · 0 pending" in judge_home.text
    assert f"/adjudicate?game_id={GAME}" in judge_home.text
    ready(world)
    run(world, "submit")
    run(world, "amend", effective_version=1)
    assert "Amendment review · 1 pending" in judge.get("/").text


@pytest.mark.parametrize("htmx", [False, True])
def test_form_validation_conflict_recovery_and_csrf(world, htmx):
    client = client_for(world)
    page = client.get(f"/play?game_id={GAME}")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text)[1]
    url = f"/workspace/{GAME}/team-0/1/form"
    assert client.post(url, data={}).status_code == 403
    data = dict(
        csrf_token=csrf,
        operation="intention",
        expected_version=0,
        key=str(uuid4()),
        overall_intention="first",
    )
    headers = {"HX-Request": "true"} if htmx else {}
    assert client.post(url, data=data, headers=headers).status_code == 200
    data.update(key=str(uuid4()), overall_intention="my preserved attempt")
    response = client.post(url, data=data, headers=headers)
    assert response.status_code == 409
    assert "my preserved attempt" in response.text and "first" in response.text
    assert 'name="expected_version" value="1"' in response.text
    data.update(expected_version=1, key=str(uuid4()))
    assert client.post(url, data=data, headers=headers).status_code == 200
    bad = dict(
        csrf_token=csrf,
        operation="action",
        expected_version=2,
        key=str(uuid4()),
        title="Incomplete",
    )
    assert client.post(url, data=bad).status_code == 200
    response = client.post(
        url, data=dict(csrf_token=csrf, operation="submit", expected_version=3, key=str(uuid4()))
    )
    assert response.status_code == 422 and "Complete all four fields" in response.text


def test_malformed_form_retains_non_secret_values(world):
    client = client_for(world)
    page = client.get(f"/play?game_id={GAME}&edit=new-action")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text)[1]
    response = client.post(
        f"/workspace/{GAME}/team-0/1/form",
        data={
            "csrf_token": csrf,
            "operation": "action",
            "expected_version": "0",
            "key": str(uuid4()),
            "owner_user_id": "not-a-uuid",
            "title": "Retained title",
            "description": "Retained description",
            "intent": "Retained intent",
            "anticipated_reaction": "Retained reaction",
        },
    )
    assert response.status_code == 422
    for value in ("Retained title", "Retained description", "Retained intent", "Retained reaction"):
        assert value in response.text


def test_malformed_comment_and_decision_retain_authored_values(world):
    ready(world)
    client = client_for(world)
    csrf = workspace_csrf(client)
    with world[0].transaction() as session:
        action_id = session.scalar(select(DraftAction.id))
    comment = client.post(
        f"/workspace/{GAME}/team-0/1/form",
        data={
            "csrf_token": csrf,
            "operation": "comment",
            "expected_version": "not-a-version",
            "key": str(uuid4()),
            "action_id": str(action_id),
            "comment": "Retained schema-invalid comment",
        },
    )
    assert comment.status_code == 422
    assert "Retained schema-invalid comment" in comment.text

    run(world, "submit")
    run(world, "intention", overall_intention="Amended")
    run(world, "amend", effective_version=1)
    judge = client_for(world, "judge")
    adjudicate = judge.get(f"/adjudicate?game_id={GAME}")
    judge_csrf = re.search(r'name="csrf_token" value="([^"]+)"', adjudicate.text)[1]
    with world[0].transaction() as session:
        amendment_id = session.scalar(select(Amendment.id))
    decision = judge.post(
        f"/workspace/{GAME}/team-0/1/form",
        data={
            "csrf_token": judge_csrf,
            "operation": "decide",
            "expected_version": "not-a-version",
            "key": str(uuid4()),
            "amendment_id": str(amendment_id),
            "decision": "rejected",
            "reason": "Retained schema-invalid decision reason",
        },
    )
    assert decision.status_code == 422
    assert "Retained schema-invalid decision reason" in decision.text
    assert re.search(r'<option value="rejected"[^>]*selected', decision.text)


def test_submission_view_stays_frozen(world):
    ready(world)
    run(world, "submit")
    run(world, "intention", overall_intention="Unsubmitted draft")
    client = client_for(world, "judge")
    page = client.get(f"/adjudicate?game_id={GAME}")
    assert "Unsubmitted draft" not in page.text
    assert "A careful overall intention" in page.text and "Late submission" in page.text


def test_enhanced_success_acknowledges_commit_and_legacy_form_redirects(world):
    client = client_for(world)
    csrf = workspace_csrf(client)
    url = f"/workspace/{GAME}/team-0/1/form"
    legacy = client.post(
        url,
        data={
            "csrf_token": csrf,
            "operation": "intention",
            "expected_version": 0,
            "key": str(uuid4()),
            "overall_intention": "Legacy save",
        },
        follow_redirects=False,
    )
    assert legacy.status_code == 303
    assert legacy.headers["location"].endswith("&saved=intention")
    confirmation = client.get(legacy.headers["location"])
    assert "Overall intention saved." in confirmation.text
    key = str(uuid4())
    response = client.post(
        url,
        data={
            "csrf_token": csrf,
            "operation": "intention",
            "expected_version": 1,
            "key": key,
            "overall_intention": "Enhanced save",
        },
        headers=ENHANCED,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.living-memory.workspace+json"
    )
    assert response.json() == {
        "outcome": "committed",
        "operation": "intention",
        "key": key,
        "editor": "intention",
        "refresh": f"/play?game_id={GAME}&team_id=team-0&turn=1",
    }


def test_enhanced_new_action_returns_durable_editor_identity_on_replay(world):
    client = client_for(world)
    csrf = workspace_csrf(client)
    key = str(uuid4())
    data = {
        "csrf_token": csrf,
        "operation": "action",
        "expected_version": 0,
        "key": key,
        **BODY,
    }
    url = f"/workspace/{GAME}/team-0/1/form"
    first = client.post(url, data=data, headers=ENHANCED)
    assert first.status_code == 200
    editor = first.json()["editor"]
    assert re.fullmatch(r"action-[0-9a-f-]{36}", editor)
    replay = client.post(url, data=data, headers=ENHANCED)
    assert replay.status_code == 200
    assert replay.json()["editor"] == editor
    with world[0].transaction() as session:
        assert session.scalar(select(func.count()).select_from(DraftAction)) == 1


def test_enhanced_conflict_has_current_version_and_readable_context(world):
    run(world, "intention", overall_intention="Current intention")
    client = client_for(world)
    response = client.post(
        f"/workspace/{GAME}/team-0/1/form",
        data={
            "csrf_token": workspace_csrf(client),
            "operation": "intention",
            "expected_version": 0,
            "key": str(uuid4()),
            "overall_intention": "My intention",
        },
        headers=ENHANCED,
    )
    assert response.status_code == 409
    payload = response.json()
    assert payload["outcome"] == "conflict"
    assert payload["current_version"] == 1
    assert payload["conflict"] == {
        "base": {"overall_intention": ""},
        "current": {"overall_intention": "Current intention"},
        "mine": {"overall_intention": "My intention"},
    }
    assert payload["conflict_display"]["current"] == {
        "kind": "text",
        "state": "available",
        "fields": [
            {"label": "Overall intention", "value": "Current intention", "empty": False}
        ],
    }
    assert "Current intention" in payload["html"]
    assert "My intention" in payload["html"]


def test_enhanced_package_conflict_has_readable_current_state(world):
    ready(world)
    client = client_for(world)
    csrf = workspace_csrf(client)
    run(world, "intention", overall_intention="Changed after page load")
    response = client.post(
        f"/workspace/{GAME}/team-0/1/form",
        data={
            "csrf_token": csrf,
            "operation": "submit",
            "expected_version": 2,
            "key": str(uuid4()),
        },
        headers=ENHANCED,
    )
    assert response.status_code == 409
    current = response.json()["conflict_display"]["current"]
    assert current["kind"] == "package"
    assert current["fields"][0] == {
        "label": "Overall intention",
        "value": "Changed after page load",
        "empty": False,
    }
    assert "Public initiative" in current["fields"][1]["value"]
    assert str(world[2]["teammate"]) not in current["fields"][1]["value"]
    mine = response.json()["conflict_display"]["mine"]
    assert mine["fields"][0] == {
        "label": "Requested operation",
        "value": "Submit turn package",
        "empty": False,
    }


def test_enhanced_key_conflict_and_readable_retained_validation(world):
    client = client_for(world)
    csrf = workspace_csrf(client)
    url = f"/workspace/{GAME}/team-0/1/form"
    key = str(uuid4())
    initial = {
        "csrf_token": csrf,
        "operation": "intention",
        "expected_version": 0,
        "key": key,
        "overall_intention": "Original",
    }
    assert client.post(url, data=initial, headers=ENHANCED).status_code == 200
    mismatch = client.post(
        url,
        data={**initial, "overall_intention": "Changed after dispatch"},
        headers=ENHANCED,
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["outcome"] == "key_conflict"

    malformed = client.post(
        url,
        data={
            "csrf_token": csrf,
            "operation": "action",
            "expected_version": 1,
            "key": str(uuid4()),
            "owner_user_id": "not-a-uuid",
            "title": "Retained title",
            "description": "Retained description",
            "intent": "Retained intent",
            "anticipated_reaction": "Retained reaction",
        },
        headers=ENHANCED,
    )
    assert malformed.status_code == 422
    payload = malformed.json()
    assert payload["outcome"] == "validation_error"
    assert payload["errors"] == [
        {"field": "owner_user_id", "message": "Choose a valid responsible teammate."}
    ]
    assert payload["values"]["body"] == {
        "title": "Retained title",
        "description": "Retained description",
        "intent": "Retained intent",
        "anticipated_reaction": "Retained reaction",
    }
    assert "valid UUID" not in payload["html"]
    assert "Retained description" in payload["html"]


def test_enhanced_direct_rejections_keep_status_and_error_pages_do_not_disclose(world):
    anonymous = TestClient(create_app(world[1], world[0], FixedClock(NOW)))
    unauthenticated = anonymous.get(f"/play?game_id={GAME}", headers=ENHANCED)
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["outcome"] == "rejected"

    member = client_for(world, "teammate")
    url = f"/workspace/{GAME}/team-0/1/form"
    forbidden = member.post(
        url,
        data={
            "csrf_token": workspace_csrf(member),
            "operation": "submit",
            "expected_version": 0,
            "key": str(uuid4()),
        },
        headers=ENHANCED,
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["outcome"] == "rejected"
    csrf_rejection = member.post(url, data={}, headers=ENHANCED)
    assert csrf_rejection.status_code == 403
    assert csrf_rejection.json()["outcome"] == "rejected"
    missing = member.get(f"/play?game_id={GAME}&team_id=unknown", headers=ENHANCED)
    assert missing.status_code == 404
    assert missing.json()["outcome"] == "rejected"

    html_headers = {"Accept": "text/html"}
    denied_page = member.post(
        url,
        data={
            "csrf_token": workspace_csrf(member),
            "operation": "submit",
            "expected_version": 0,
            "key": str(uuid4()),
        },
        headers=html_headers,
    )
    missing_page = member.get(
        f"/play?game_id={GAME}&team_id=unknown", headers=html_headers
    )
    assert denied_page.status_code == 403
    assert missing_page.status_code == 404
    assert "<h1>Page unavailable</h1>" in denied_page.text
    assert "<h1>Page unavailable</h1>" in missing_page.text
