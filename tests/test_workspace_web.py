# ruff: noqa: F811
import re
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_admin_database import database  # noqa: F401
from test_workspace import BODY, GAME, NOW, ready, run, world  # noqa: F401

from living_memory.app import create_app
from living_memory.clocks import FixedClock
from living_memory.identity import issue_session

pytestmark = pytest.mark.integration


def client_for(world, who="player"):
    db, settings, ids = world
    with db.transaction() as session:
        token = issue_session(session, ids[who], NOW)
    client = TestClient(create_app(settings, db, FixedClock(NOW)))
    client.cookies.set("lm_auth", token)
    return client


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


def test_submission_view_stays_frozen(world):
    ready(world)
    run(world, "submit")
    run(world, "intention", overall_intention="Unsubmitted draft")
    client = client_for(world, "judge")
    page = client.get(f"/adjudicate?game_id={GAME}")
    assert "Unsubmitted draft" not in page.text
    assert "A careful overall intention" in page.text and "Late submission" in page.text
