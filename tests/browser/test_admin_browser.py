import json
import socket
import threading
import time
from datetime import UTC, datetime

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright
from test_database import database  # noqa: F401

from living_memory.app import create_app
from living_memory.clocks import FixedClock
from living_memory.identity import create_local_user

pytestmark = pytest.mark.browser


def scenario(team_count, duration, vocabulary):
    teams = []
    actors = []
    objectives = {}
    values = {}
    for index in range(team_count):
        team_id, actor_id = f"team-{index}", f"actor-{index}"
        teams.append(
            {
                "id": team_id,
                "name": f"Team {index}",
                "actor_ids": [actor_id],
                "controllers": [
                    {"kind": "human"}
                    if index == 0
                    else {"kind": "imported", "reference": f"feed-{index}"}
                ],
            }
        )
        actors.append({"id": actor_id, "name": f"Actor {index}"})
        objectives[team_id] = [f"Objective {index}"]
        values[team_id] = index + 1
    return json.dumps(
        {
            "teams": teams,
            "actors": actors,
            "rules": ["Simultaneous submissions, then joint review"],
            "objectives": objectives,
            "resources": [{"id": "capacity", "name": "Capacity", "initial_values": values}],
            "relationships": [
                {
                    "id": "representation",
                    "type": "represents",
                    "endpoints": [
                        {"entity_id": "team-0", "role": "representative"},
                        {"entity_id": "actor-0", "role": "represented"},
                    ],
                }
            ],
            "turns": [
                {
                    "number": number,
                    "simulated_duration_minutes": duration,
                    "submission_deadline": f"2040-01-0{number}T00:00:00Z",
                }
                for number in (1, 2)
            ],
            "vocabulary": vocabulary,
        }
    )


@pytest.fixture
def admin_server(database):  # noqa: F811
    db, settings = database
    now = datetime(2039, 1, 1, tzinfo=UTC)
    with db.transaction() as session:
        create_local_user(
            session, "admin", "Administrator", "admin password", now, system_admin=True
        )
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(settings, db, FixedClock(now)), log_level="warning", access_log=False
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                pytest.fail("Admin browser server did not start")
            time.sleep(0.01)
        yield f"http://127.0.0.1:{sock.getsockname()[1]}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


@pytest.mark.parametrize("javascript", [True, False])
def test_login_user_and_two_scenario_workflows(admin_server, javascript):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(java_script_enabled=javascript)
        page.goto(admin_server + "/login")
        page.get_by_label("Username").fill("ADMIN")
        page.get_by_label("Password").fill("admin password")
        page.get_by_role("button", name="Sign in").focus()
        with page.expect_navigation():
            page.keyboard.press("Enter")
        expect(page).to_have_url(admin_server + "/")
        page.goto(admin_server + "/admin")
        expect(page.get_by_role("heading", name="Administration")).to_be_visible()

        page.get_by_text("Create local user").click()
        page.get_by_label("Username", exact=True).fill("planner")
        page.get_by_label("Display name").fill("Scenario Planner")
        page.get_by_label("Initial password").fill("planner password")
        page.get_by_role("button", name="Create user").click()
        expect(page.get_by_role("button", name="Deactivate planner")).to_be_visible()

        for game_id, title, configuration in (
            ("harbor-relief", "Harbor Relief", scenario(2, 1440, ["relief", "port"])),
            ("orchid-accord", "Orchid Accord", scenario(3, 720, ["orchid", "pollination"])),
        ):
            page.get_by_text("Create configured game").click()
            game_form = page.locator('form[action="/admin/games"]')
            game_form.get_by_label("Stable identifier").fill(game_id)
            game_form.get_by_label("Title").fill(title)
            game_form.get_by_label("Public description").fill(f"Public description for {title}")
            game_form.get_by_label("Public rules").fill("Public rules")
            game_form.get_by_label("Open-source briefing").fill("Public briefing")
            game_form.get_by_label("Structured configuration (JSON)").fill(configuration)
            game_form.get_by_role("button", name="Create draft game").click()
            expect(page.get_by_text(title, exact=True).first).to_be_visible()
        expect(page.get_by_text("draft, turn 0")).to_have_count(2)

        page.get_by_role("button", name="Sign out").click()
        expect(page.get_by_role("heading", name="Sign in")).to_be_visible()
        browser.close()
