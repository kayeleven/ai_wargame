import json
import socket
import threading
import time
from datetime import UTC, datetime
from urllib.parse import urlencode, urlsplit

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright
from sqlalchemy import select
from test_admin_database import config
from test_database import database  # noqa: F401
from test_memory import timeline  # noqa: F401

from living_memory.administration import activate_game, create_game
from living_memory.app import create_app
from living_memory.clocks import FixedClock
from living_memory.db import ROOT, DevelopmentArtifact
from living_memory.identity import GameRole, TeamMembership, create_local_user
from living_memory.memory import load_timeline
from living_memory.seed import stage_package

pytestmark = pytest.mark.browser


@pytest.fixture
def memory_server(timeline):  # noqa: F811
    db, settings, dataset = timeline
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    app = create_app(settings.model_copy(update={"environment": "development"}), db)
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                pytest.fail("Memory server did not start")
            time.sleep(0.01)
        yield f"http://127.0.0.1:{sock.getsockname()[1]}", str(dataset)
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


@pytest.fixture
def dual_memory_server(database):  # noqa: F811
    db, settings = database
    clock = FixedClock(datetime(2045, 1, 1, tzinfo=UTC))
    for name in ("phase0", "orchid-accord"):
        stage_package(db, clock, ROOT / "fixtures" / name)
    with db.transaction() as session:
        artifacts = list(session.scalars(select(DevelopmentArtifact)))
    for artifact in artifacts:
        assert load_timeline(db, artifact.checksum)
    datasets = {artifact.package: str(artifact.id) for artifact in artifacts}
    with db.transaction() as session:
        administrator = create_local_user(
            session,
            "fixture-admin",
            "Fixture administrator",
            "test password",
            clock.now(),
            system_admin=True,
        )
        game = create_game(
            session,
            "operational-alongside-fixtures",
            "Operational game",
            config(),
            administrator.id,
            clock.now(),
        )
        session.add(
            GameRole(
                user_id=administrator.id,
                game_id=game.id,
                role="adjudicator",
                granted_at=clock.now(),
                granted_by=administrator.id,
            )
        )
        session.add_all(
            TeamMembership(
                user_id=administrator.id,
                game_id=game.id,
                team_id=team_id,
                authority="submitter",
                granted_at=clock.now(),
                granted_by=administrator.id,
            )
            for team_id in ("team-0", "team-1")
        )
        activate_game(session, game, administrator.id, clock.now())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    app = create_app(settings.model_copy(update={"environment": "development"}), db)
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                pytest.fail("Memory server did not start")
            time.sleep(0.01)
        yield f"http://127.0.0.1:{sock.getsockname()[1]}", datasets
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


@pytest.mark.parametrize("javascript", [True, False])
def test_audiences_checkpoints_and_evidence(memory_server, javascript):
    server, dataset = memory_server
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(java_script_enabled=javascript)
        external = []
        page.on(
            "request",
            lambda r: (
                external.append(r.url)
                if urlsplit(r.url).netloc != urlsplit(server).netloc
                else None
            ),
        )
        for audience, identity in [
            ("adjudicator", "reviewer"),
            ("estuary", "estuary-member"),
            ("upland", "upland-member"),
        ]:
            for checkpoint in ["t3", "review", "release"]:
                params = {"dataset": dataset, "identity": identity, "checkpoint": checkpoint}
                page.goto(server + "/dev/memory?" + urlencode(params))
                expected = json.loads(
                    (ROOT / f"fixtures/phase0/views/{checkpoint}-{audience}.json").read_text()
                )
                assert set(
                    page.locator("article.memory-record").evaluate_all(
                        "(els) => els.map(e => e.id)"
                    )
                ) == {r["id"] for r in expected["records"]}
                label = {
                    "estuary": "Visible to Estuary Council",
                    "upland": "Visible to Upland Council",
                    "adjudicator": "Visible to adjudicator",
                }[audience]
                expect(page.locator("article .visibility-label")).to_have_text(
                    [label] * len(expected["records"])
                )
                if audience != "adjudicator":
                    expect(
                        page.get_by_label("Audience", exact=True).locator("option")
                    ).to_have_count(1)
                links = page.locator('nav[aria-label^="Evidence"] a')
                if links.count():
                    target = links.first.get_attribute("href")
                    links.first.click()
                    expect(page.locator("article.memory-record")).to_have_count(1)
                    expect(page.locator("article .visibility-label")).to_have_text(label)
                    assert "checkpoint=" + checkpoint in target
                    expect(page.get_by_role("link", name="Back to task view")).to_be_visible()
        page.goto(
            server
            + "/dev/memory?"
            + urlencode({"dataset": dataset, "identity": "reviewer", "record": "upland-t4-v1"})
        )
        expect(page.get_by_role("heading", name="Inspect civilian invoices")).to_be_visible()
        expect(
            page.get_by_text(
                "We will inspect suspect trade invoices soon using available staff.", exact=True
            )
        ).to_be_visible()
        page.get_by_label("Development identity").select_option("estuary-member")
        page.get_by_role("button", name="Switch identity").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#upland-t4-v1")).to_have_count(0)
        assert external == []
        browser.close()


@pytest.mark.parametrize("javascript", [True, False])
def test_dataset_switch_and_multi_scope_fixture(dual_memory_server, javascript):
    server, datasets = dual_memory_server
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(java_script_enabled=javascript)
        page.goto(
            server
            + "/dev/memory?"
            + urlencode(
                {
                    "dataset": datasets["orchid-accord-adversarial"],
                    "identity": "multi-reader",
                    "audience": "amber",
                    "checkpoint": "late",
                }
            )
        )
        expect(page.get_by_label("Audience", exact=True).locator("option")).to_have_count(2)
        expect(
            page.get_by_label("Record type").locator('option[value="orchid:pollination-log"]')
        ).to_have_count(1)
        expect(page.locator("#hidden-carrier")).to_have_count(0)
        expect(page.get_by_text("orchid:cross-pollinates", exact=False)).to_have_count(0)
        page.get_by_label("Dataset").select_option(datasets["harbor-relief-acceptance"])
        page.get_by_role("button", name="Show memory").click()
        expect(page.get_by_role("heading", name="Harbor Relief")).to_be_visible()
        expect(page.get_by_label("Development identity")).to_have_value("estuary-member")
        browser.close()
