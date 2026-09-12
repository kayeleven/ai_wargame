# ruff: noqa: F811
"""Real Chromium smoke and shared-edit/amendment workflow, plain and HTMX forms."""

import socket
import threading
import time

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright
from test_admin_database import database  # noqa: F401
from test_workspace import GAME, NOW, world  # noqa: F401

from living_memory.app import create_app
from living_memory.clocks import FixedClock
from living_memory.identity import issue_session

pytestmark = pytest.mark.browser


@pytest.fixture
def workspace_server(world):
    db, settings, ids = world
    tokens = {}
    with db.transaction() as s:
        for name, uid in ids.items():
            tokens[name] = issue_session(s, uid, NOW)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(settings, db, FixedClock(NOW)), log_level="warning", access_log=False
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                pytest.fail("Workspace server failed to start")
            time.sleep(0.01)
        yield f"http://127.0.0.1:{sock.getsockname()[1]}", tokens
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


def page_for(browser, url, tokens, name, javascript):
    context = browser.new_context(java_script_enabled=javascript)
    context.add_cookies([dict(name="lm_auth", value=tokens[name], url=url)])
    return context.new_page()


@pytest.mark.parametrize("javascript", [False, True])
def test_draft_submit_smoke(workspace_server, javascript):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", javascript)
        page.goto(f"{url}/play?game_id={GAME}")
        page.get_by_label("Overall intention", exact=True).fill("Observe and report")
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_text("Draft revision 1.", exact=False)).to_be_visible()
        page.get_by_role("button", name="Submit turn package", exact=True).click()
        expect(page.get_by_text("Effective version 1 · submitted.", exact=True)).to_be_visible()
        expect(page.get_by_text("Late submission", exact=True)).to_be_visible()
        for name in ("Import", "Submit RFI", "Coordination"):
            expect(page.get_by_role("button", name=name, exact=True)).to_have_count(0)
        browser.close()


@pytest.mark.parametrize("javascript", [False, True])
def test_shared_conflict_and_amendment_decision(workspace_server, javascript):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        player = page_for(browser, url, tokens, "player", javascript)
        mate = page_for(browser, url, tokens, "teammate", javascript)
        judge = page_for(browser, url, tokens, "judge", javascript)
        for page in (player, mate):
            page.goto(f"{url}/play?game_id={GAME}")
        player.get_by_label("Overall intention", exact=True).fill("First intention")
        player.get_by_role("button", name="Save intention", exact=True).click()
        expect(player.get_by_text("Draft revision 1.", exact=False)).to_be_visible()
        mate.get_by_label("Overall intention", exact=True).fill("Teammate correction")
        mate.get_by_role("button", name="Save intention", exact=True).click()
        expect(mate.get_by_role("heading", name="Edit conflict")).to_be_visible()
        expect(mate.get_by_label("Overall intention", exact=True)).to_have_value(
            "Teammate correction"
        )
        mate.get_by_role("button", name="Save intention", exact=True).click()
        expect(mate.get_by_text("Draft revision 2.", exact=False)).to_be_visible()
        player.reload()
        player.get_by_role("button", name="Submit turn package", exact=True).click()
        expect(player.get_by_text("Effective version 1 · submitted.", exact=True)).to_be_visible()
        player.get_by_label("Overall intention", exact=True).fill("Proposed change")
        player.get_by_role("button", name="Save intention", exact=True).click()
        expect(player.get_by_text("Draft revision 4.", exact=False)).to_be_visible()
        player.get_by_role("button", name="Propose amendment", exact=True).click()
        expect(player.get_by_text("amendment_pending", exact=False)).to_be_visible()
        judge.goto(f"{url}/adjudicate?game_id={GAME}")
        judge.get_by_label("Reason", exact=True).fill("Clarifies the intent")
        judge.get_by_role("button", name="Record amendment decision", exact=True).click()
        expect(judge.get_by_text("Effective version 2 · submitted.", exact=True)).to_be_visible()
        browser.close()


@pytest.mark.parametrize("javascript", [False, True])
def test_rejected_decision_survives_validation(workspace_server, world, javascript):
    from test_workspace import ready, run

    ready(world)
    run(world, "submit")
    run(world, "amend", effective_version=1)
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        judge = page_for(browser, url, tokens, "judge", javascript)
        judge.goto(f"{url}/adjudicate?game_id={GAME}")
        judge.get_by_label("Decision", exact=True).select_option("rejected")
        judge.get_by_role("button", name="Record amendment decision", exact=True).click()
        expect(judge.get_by_role("heading", name="Please check your input")).to_be_visible()
        expect(judge.get_by_label("Decision", exact=True)).to_have_value("rejected")
        judge.get_by_label("Reason", exact=True).fill("Reject after correcting validation")
        judge.get_by_role("button", name="Record amendment decision", exact=True).click()
        expect(judge.get_by_text("Effective version 1 · submitted.", exact=True)).to_be_visible()
        expect(
            judge.get_by_role("heading", name="Version 2 proposed against version 1 — rejected")
        ).to_be_visible()
        browser.close()
