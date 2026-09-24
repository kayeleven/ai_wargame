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


def test_exact_deadline_first_submission_is_late_in_player_and_adjudicator_views(world):
    """The service stores and both views display the inclusive deadline boundary."""
    from test_admin_database import config

    from living_memory.administration import ConfigurationRevision
    from living_memory.workspace import Submission

    ready(world)
    with world[0].transaction() as session:
        previous = session.scalar(
            select(ConfigurationRevision).where(ConfigurationRevision.game_id == GAME)
        )
        revised = config().model_dump(mode="json")
        revised["turns"][0]["submission_deadline"] = NOW.isoformat()
        session.add(
            ConfigurationRevision(
                game_id=GAME,
                sequence=previous.sequence + 1,
                effective_turn=1,
                recorded_at=NOW,
                configuration=revised,
                supersedes_revision_id=previous.id,
                author_user_id=world[2]["admin"],
            )
        )
    # run() executes the confirmed command with FixedClock(NOW), so this is a
    # real first submission at the configured stored deadline.
    run(world, "submit")
    with world[0].transaction() as session:
        submission = session.scalar(select(Submission))
        assert submission.submitted_at == submission.deadline == NOW

    assert "Late submission" in client_for(world).get(f"/play?game_id={GAME}").text
    assert "Late submission" in client_for(world, "judge").get(
        f"/adjudicate?game_id={GAME}"
    ).text


def test_effective_overview_enters_revision_mode_without_changing_saved_draft(world):
    """Revision entry is a read-only transition until a player saves or submits."""
    from test_workspace import counts

    ready(world)
    run(world, "submit")
    run(world, "intention", overall_intention="Saved revision draft")
    client = client_for(world)
    before = counts(world[0])

    overview = client.get(f"/play?game_id={GAME}")
    assert overview.status_code == 200
    assert "Effective package" in overview.text
    assert "Revise saved draft" in overview.text
    assert "mode=revise" in overview.text
    assert counts(world[0]) == before

    revision = client.get(f"/play?game_id={GAME}&mode=revise")
    assert revision.status_code == 200
    assert 'name="overall_intention">Saved revision draft</textarea>' in revision.text
    assert "Submit revision" in revision.text
    assert counts(world[0]) == before


def test_revision_consequence_hint_is_a_rule_and_members_cannot_submit(world):
    from datetime import timedelta

    from living_memory.administration import AdminGame
    from living_memory.workspace_service import get_submission

    ready(world)
    run(world, "submit")
    with world[0].transaction() as session:
        get_submission(session, GAME, "team-0", 1).deadline = NOW + timedelta(minutes=5)

    submitter = client_for(world)
    page = submitter.get(f"/play?game_id={GAME}&mode=revise")
    assert "Before the deadline, revisions take effect immediately." in page.text
    assert "At or after the deadline, revisions require adjudicator acceptance." in page.text
    assert "This revision will take effect immediately" not in page.text

    member = client_for(world, "teammate")
    member_page = member.get(f"/play?game_id={GAME}&mode=revise")
    assert "Submit revision" not in member_page.text
    assert "Only the designated submitter can submit revisions." in member_page.text

    with world[0].transaction() as session:
        session.get(AdminGame, GAME).current_turn = 2
    historical = submitter.get(f"/play?game_id={GAME}&turn=1&mode=revise")
    assert "This turn is read-only." in historical.text
    assert "Submit revision" not in historical.text


def test_pending_revision_allows_saved_draft_edits_but_not_another_submission(world):
    ready(world)
    run(world, "submit")
    run(world, "amend", effective_version=1)
    client = client_for(world)
    csrf = workspace_csrf(client)

    page = client.get(f"/play?game_id={GAME}&mode=revise")
    assert "Amendment pending" in page.text
    assert re.search(r"<button[^>]*disabled[^>]*>Submit revision</button>", page.text)
    response = client.post(
        f"/workspace/{GAME}/team-0/1/form?mode=revise",
        data={
            "csrf_token": csrf,
            "operation": "intention",
            "expected_version": 2,
            "key": str(uuid4()),
            "overall_intention": "Correction while pending",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "mode=revise" in response.headers["location"]
    assert "Correction while pending" in client.get(response.headers["location"]).text


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
        "committed_draft_version": 2,
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
    assert first.json()["committed_draft_version"] == 1
    assert re.fullmatch(r"action-[0-9a-f-]{36}", editor)
    run(world, "intention", overall_intention="Later unrelated change")
    replay = client.post(url, data=data, headers=ENHANCED)
    assert replay.status_code == 200
    assert replay.json()["editor"] == editor
    assert replay.json()["committed_draft_version"] == 1
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
    assert malformed.headers["content-type"].startswith(
        "application/vnd.living-memory.workspace+json"
    )
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


def test_access_revoked_before_enhanced_error_render_is_confirmed_rejection(
    world, monkeypatch
):
    from living_memory.identity import User

    client = client_for(world)
    csrf = workspace_csrf(client)

    def revoke_then_fail(*args, **kwargs):
        with world[0].transaction() as session:
            session.get(User, world[2]["player"]).active = False
        raise ValueError("Enter a comment")

    monkeypatch.setattr("living_memory.workspace_web.execute", revoke_then_fail)
    response = client.post(
        f"/workspace/{GAME}/team-0/1/form",
        data={
            "csrf_token": csrf,
            "operation": "comment",
            "expected_version": 0,
            "key": str(uuid4()),
            "comment": "Attempted comment",
        },
        headers=ENHANCED,
    )
    with world[0].transaction() as session:
        session.get(User, world[2]["player"]).active = True
    assert response.status_code == 401
    assert response.json()["outcome"] == "rejected"


def test_review_selection_immutable_versions_and_scoped_links(world):
    from test_workspace import review_history

    rejected, pending = review_history(world)
    judge = client_for(world, "judge")
    run(world, "intention", overall_intention="UNSUBMITTED SECRET DRAFT")
    path = f"/adjudicate?game_id={GAME}"
    page = judge.get(path)
    assert page.status_code == 200
    assert "Version 3 proposed against version 1 — pending" in page.text
    assert "Pending proposal" in page.text and "UNSUBMITTED SECRET DRAFT" not in page.text
    assert "Rejected proposal" not in page.text
    history = judge.get(f"{path}&amendment_id={rejected}")
    assert "Rejected proposal" in history.text and "Pending proposal" not in history.text
    assert 'name="decision"' not in history.text
    assert "Preserved rejection reason" in history.text
    assert judge.get(f"{path}&amendment_id={uuid4()}").status_code == 404
    assert judge.get(f"{path}&team_id=team-1&amendment_id={pending}").status_code == 404
    assert client_for(world).get(f"{path}&amendment_id={pending}").status_code == 404
    player = client_for(world)
    assert "revision=2#submission-2" in player.get(f"/play?game_id={GAME}").text
    revision = player.get(f"/play?game_id={GAME}&revision=2")
    assert re.search(r'<details id="submission-2"\s+open', revision.text)
    assert player.get(f"/play?game_id={GAME}&revision=999").status_code == 404
    assert client_for(world, "other").get(f"/play?game_id={GAME}&revision=2").status_code == 404


def test_review_historical_owner_and_missing_immutable_version(world):
    from living_memory.identity import User
    from living_memory.workspace import SubmissionVersion

    ready(world)
    run(world, "submit")
    run(world, "amend", effective_version=1)
    with world[0].transaction() as session:
        session.get(User, world[2]["teammate"]).active = False
    judge = client_for(world, "judge")
    page = judge.get(f"/adjudicate?game_id={GAME}")
    assert "Teammate" in page.text and "Former teammate" not in page.text
    # Proposed versions have no effective-version FK; simulate unsupported legacy corruption.
    with world[0].transaction() as session:
        session.delete(
            session.scalar(select(SubmissionVersion).where(SubmissionVersion.version == 2))
        )
    page = judge.get(f"/adjudicate?game_id={GAME}")
    assert "Comparison unavailable" in page.text
    assert 'name="decision"' not in page.text


@pytest.mark.parametrize("enhanced", [False, True])
def test_decision_responses_preserve_selected_amendment(world, enhanced):
    from test_workspace import review_history

    from living_memory.workspace_service import get_submission

    rejected, pending = review_history(world)
    judge = client_for(world, "judge")
    page = judge.get(f"/adjudicate?game_id={GAME}")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text)[1]
    with world[0].transaction() as session:
        version = get_submission(session, GAME, "team-0", 1).version
    data = dict(
        csrf_token=csrf,
        operation="decide",
        expected_version=version,
        key=str(uuid4()),
        amendment_id=str(pending),
        decision="rejected",
        reason="",
    )
    endpoint = f"/workspace/{GAME}/team-0/1/form"
    headers = ENHANCED if enhanced else {}
    response = judge.post(endpoint, data=data, headers=headers)
    assert response.status_code == 422
    html = response.json()["html"] if enhanced else response.text
    assert "Version 3 proposed against version 1 — pending" in html
    assert f'id="editor-decision-{pending}"' in html
    data["reason"] = "Specific reason"
    response = judge.post(endpoint, data=data, headers=headers, follow_redirects=False)
    assert response.status_code == (200 if enhanced else 303)
    target = response.json()["refresh"] if enhanced else response.headers["location"]
    assert f"amendment_id={pending}" in target
    replay = judge.post(endpoint, data=data, headers=headers, follow_redirects=False)
    assert (replay.json()["refresh"] if enhanced else replay.headers["location"]) == target
    assert "Specific reason" in judge.get(target).text
    assert (
        "Specific reason"
        not in judge.get(f"/adjudicate?game_id={GAME}&amendment_id={rejected}").text
    )


def test_ordinary_stale_decision_keeps_attempted_reason(world):
    from test_workspace import review_history, run

    from living_memory.workspace_service import get_submission

    _, pending = review_history(world)
    judge = client_for(world, "judge")
    page = judge.get(f"/adjudicate?game_id={GAME}")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text)[1]
    with world[0].transaction() as session:
        version = get_submission(session, GAME, "team-0", 1).version
    run(
        world,
        "decide",
        version,
        who="judge",
        amendment_id=pending,
        decision="accepted",
        reason="Already accepted",
    )
    response = judge.post(
        f"/workspace/{GAME}/team-0/1/form",
        data=dict(
            csrf_token=csrf,
            operation="decide",
            expected_version=version,
            key=str(uuid4()),
            amendment_id=str(pending),
            decision="rejected",
            reason="My stale reason",
        ),
    )
    assert response.status_code == 409
    assert "Already accepted" in response.text and "My stale reason" in response.text
    assert "<textarea readonly>My stale reason</textarea>" in response.text
    assert 'name="decision"' not in response.text


def test_rejected_then_pending_retains_rejection_notice(world):
    from test_workspace import review_history

    review_history(world)  # Revision 2 rejected; correction 3 pending.
    page = client_for(world).get(f"/play?game_id={GAME}")
    notice = re.search(r'<section data-workspace-region="rejection-notice">(.*?)</section>',
                       page.text, re.DOTALL)[1]
    assert "Revision 2 rejected" in notice
    assert "Preserved rejection reason" in notice
    assert "revision=2#submission-2" in notice
    assert "Effective version 1 · Amendment pending." in page.text


def test_rejected_then_accepted_clears_notice_without_erasing_history(world):
    from test_workspace import review_history

    from living_memory.workspace_service import get_submission

    _, pending = review_history(world)
    with world[0].transaction() as session:
        version = get_submission(session, GAME, "team-0", 1).version
    run(world, "decide", version, who="judge", amendment_id=pending,
        decision="accepted", reason="Correction accepted")
    player = client_for(world)
    page = player.get(f"/play?game_id={GAME}")
    assert "View rejected revision" not in page.text
    assert "Revision 2 rejected" not in page.text
    assert "Preserved rejection reason" in page.text
    assert "Correction accepted" in page.text
    assert 'Effective version 3' in page.text
    # A further pending revision must not revive the superseded rejection.
    run(world, "amend", effective_version=3)
    page = player.get(f"/play?game_id={GAME}")
    assert "Effective version 3 · Amendment pending." in page.text
    assert "View rejected revision" not in page.text
    assert "Preserved rejection reason" in page.text


def test_new_rejection_replaces_previous_notice(world):
    from test_workspace import review_history

    from living_memory.workspace_service import get_submission

    _, pending = review_history(world)
    with world[0].transaction() as session:
        version = get_submission(session, GAME, "team-0", 1).version
    run(world, "decide", version, who="judge", amendment_id=pending,
        decision="rejected", reason="Updated reason for correction")
    page = client_for(world).get(f"/play?game_id={GAME}")
    notice = re.search(r'<section data-workspace-region="rejection-notice">(.*?)</section>',
                       page.text, re.DOTALL)[1]
    assert "Revision 3 rejected" in notice
    assert "Updated reason for correction" in notice
    assert "Preserved rejection reason" not in notice
    assert "revision=3#submission-3" in notice


def test_comparison_summary_omits_zero_counts_and_handles_empty_packages(world):
    run(world, "intention", overall_intention="Intention without actions")
    run(world, "submit")
    run(world, "amend", effective_version=1)
    page = client_for(world, "judge").get(f"/adjudicate?game_id={GAME}")
    assert "No actions in either version." in page.text
    for label in ("added", "removed", "changed", "unchanged"):
        assert f"0 {label}" not in page.text


@pytest.mark.parametrize("operation", ["submit", "amend", "decide"])
@pytest.mark.parametrize("enhanced", [False, True])
def test_completed_replay_after_turn_advance_refreshes_original_turn(world, operation, enhanced):
    from urllib.parse import parse_qs, urlsplit

    from test_workspace_command_hardening import prepared

    from living_memory.administration import AdminGame

    command, who = prepared(world, operation)
    client = client_for(world, who)
    route = "/adjudicate" if who == "judge" else "/play"
    page = client.get(f"{route}?game_id={GAME}&team_id=team-0&turn=1")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text)[1]
    values = command.model_dump(mode="json", exclude_defaults=True)
    values["csrf_token"] = csrf
    endpoint = f"/workspace/{GAME}/team-0/1/form"
    headers = ENHANCED if enhanced else {}
    original = client.post(endpoint, data=values, headers=headers, follow_redirects=False)
    assert original.status_code == (200 if enhanced else 303)
    with world[0].transaction() as session:
        session.get(AdminGame, GAME).current_turn = 2
    replay = client.post(endpoint, data=values, headers=headers, follow_redirects=False)
    assert replay.status_code == original.status_code
    if enhanced:
        assert replay.json() == original.json()
        assert replay.json()["outcome"] == "committed"
        assert replay.json()["key"] == str(command.key)
        refresh = replay.json()["refresh"]
    else:
        refresh = replay.headers["location"]
        assert refresh == original.headers["location"]
    assert parse_qs(urlsplit(refresh).query)["turn"] == ["1"]
    assert client.get(refresh).status_code == 200


def test_transaction_retry_reads_clock_again(world, monkeypatch):
    from datetime import timedelta

    from sqlalchemy import select
    from test_workspace_command_hardening import ControlledClock

    from living_memory import workspace_web
    from living_memory.team_authority import RetryableConflict
    from living_memory.workspace import EffectiveVersionEvent, RequestKey

    ready(world)
    clock = ControlledClock()
    client = client_for(world)
    client.app.state.clock = clock
    csrf = workspace_csrf(client)
    original_execute = workspace_web.execute
    attempts = []

    def transient_failure(*args, **kwargs):
        result = original_execute(*args, **kwargs)
        attempts.append(clock.now())
        if len(attempts) == 1:
            clock.advance(NOW + timedelta(seconds=10))
            raise RetryableConflict("Retry the transaction")
        return result

    monkeypatch.setattr(workspace_web, "execute", transient_failure)
    key = uuid4()
    response = client.post(f"/workspace/{GAME}/team-0/1/form", headers=ENHANCED,
                           data=dict(csrf_token=csrf, key=str(key), operation="submit",
                                     expected_version=2))
    assert response.status_code == 409
    confirmation = response.json()["confirm"]
    key = confirmation["key"]
    response = client.post(f"/workspace/{GAME}/team-0/1/form", headers=ENHANCED,
                           data={**confirmation, "csrf_token": csrf})
    assert response.status_code == 200 and response.json()["outcome"] == "committed"
    assert attempts == [NOW, NOW + timedelta(seconds=10)]
    with world[0].transaction() as session:
        assert session.scalars(select(EffectiveVersionEvent)).one().effective_at == attempts[1]
        record = session.scalars(select(RequestKey).where(RequestKey.key == key)).one()
        assert record.created_at == attempts[1]


@pytest.mark.parametrize("enhanced", [False, True])
@pytest.mark.parametrize(
    ("pending", "status", "display_status"),
    [(False, "submitted", "Submitted"), (True, "amendment_pending", "Amendment pending")],
)
def test_submission_eligibility_conflict_names_current_status(
    world, enhanced, pending, status, display_status
):
    ready(world)
    client = client_for(world)
    csrf = workspace_csrf(client)
    # A stale tab of the designated submitter races another tab's committed command.
    run(world, "submit")
    if pending:
        run(world, "amend", effective_version=1)
    response = client.post(
        f"/workspace/{GAME}/team-0/1/form",
        data={
            "csrf_token": csrf,
            "operation": "amend" if pending else "submit",
            "expected_version": 3 if pending else 2,
            "effective_version": 1 if pending else "",
            "key": str(uuid4()),
        },
        headers=ENHANCED if enhanced else {},
    )
    assert response.status_code == 409
    if enhanced:
        payload = response.json()
        assert payload["outcome"] == "conflict"
        assert payload["conflict"]["current"] == {
            "submission_status": status, "effective_version": 1,
        }
        fields = payload["conflict_display"]["current"]["fields"]
        assert {"label": "Submission status", "value": display_status, "empty": False} in fields
        assert {"label": "Effective version", "value": 1, "empty": False} in fields
        html = payload["html"]
    else:
        html = response.text
    current = re.search(r"<h3>Current</h3>(.*?)<h3>Mine</h3>", html, re.S)[1]
    assert f'<dt>Submission status</dt><dd class="authored">{display_status}</dd>' in current
    assert '<dt>Effective version</dt><dd class="authored">1</dd>' in current
