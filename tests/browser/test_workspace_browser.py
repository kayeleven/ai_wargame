# ruff: noqa: F811
"""Real Chromium smoke and shared-edit/amendment workflow, plain and HTMX forms."""

import re
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
        page.goto(f"{url}/play?game_id={GAME}" + ("" if javascript else "&edit=intention"))
        page.get_by_label("Overall intention", exact=True).fill("Observe and report")
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_text("Draft revision 1.", exact=False)).to_be_visible()
        expect(page.get_by_text("Overall intention saved.", exact=True)).to_be_visible()
        page.get_by_role("button", name="Submit turn package", exact=True).click()
        expect(page.get_by_text("Effective version 1 · submitted.", exact=True)).to_be_visible()
        expect(page.get_by_text("Turn package submitted.", exact=True)).to_be_visible()
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
            page.goto(
                f"{url}/play?game_id={GAME}" + ("" if javascript else "&edit=intention")
            )
        player.get_by_label("Overall intention", exact=True).fill("First intention")
        player.get_by_role("button", name="Save intention", exact=True).click()
        expect(player.get_by_text("Draft revision 1.", exact=False)).to_be_visible()
        mate.get_by_label("Overall intention", exact=True).fill("Teammate correction")
        mate.get_by_role("button", name="Save intention", exact=True).click()
        expect(mate.get_by_role("heading", name="Edit conflict")).to_be_visible()
        expect(mate.get_by_label("Overall intention", exact=True)).to_have_value(
            "Teammate correction"
        )
        if javascript:
            expect(mate.locator('[data-editor="intention"]')).to_have_attribute(
                "data-dirty", "true"
            )
            expect(mate.get_by_text("Resolve the saved-value conflict", exact=True)).to_be_visible()
            mate.get_by_role("button", name="Save mine", exact=True).click()
        else:
            expect(mate.get_by_text("Edit this value to combine Mine with Current")).to_be_visible()
            mate.get_by_role("button", name="Save edited value", exact=True).click()
        expect(mate.get_by_text("Draft revision 2.", exact=False)).to_be_visible()
        player.reload()
        player.get_by_role("button", name="Submit turn package", exact=True).click()
        expect(player.get_by_text("Effective version 1 · submitted.", exact=True)).to_be_visible()
        if not javascript:
            player.get_by_role("link", name="Edit overall intention").click()
        player.get_by_label("Overall intention", exact=True).fill("Proposed change")
        player.get_by_role("button", name="Save intention", exact=True).click()
        expect(player.get_by_text("Draft revision 4.", exact=False)).to_be_visible()
        player.get_by_role("button", name="Propose amendment", exact=True).click()
        expect(player.get_by_text("amendment_pending", exact=False)).to_be_visible()
        judge.goto(f"{url}/adjudicate?game_id={GAME}")
        if not javascript:
            judge.get_by_role("link", name="Review amendment decision").click()
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
        if not javascript:
            judge.get_by_role("link", name="Review amendment decision").click()
        judge.get_by_label("Decision", exact=True).select_option("rejected")
        judge.get_by_role("button", name="Record amendment decision", exact=True).click()
        expect(judge.get_by_role("heading", name="Please check your input")).to_be_visible()
        expect(judge.get_by_label("Decision", exact=True)).to_have_value("rejected")
        if javascript:
            expect(judge.locator('form[data-editor^="decision-"]')).to_have_attribute(
                "data-dirty", "true"
            )
        judge.get_by_label("Reason", exact=True).fill("Reject after correcting validation")
        judge.get_by_role("button", name="Record amendment decision", exact=True).click()
        expect(judge.get_by_text("Effective version 1 · submitted.", exact=True)).to_be_visible()
        expect(
            judge.get_by_role("heading", name="Version 2 proposed against version 1 — rejected")
        ).to_be_visible()
        browser.close()


def test_independent_dirty_editor_survives_save_and_blocks_submission(workspace_server, world):
    from test_workspace import BODY, ready

    ready(world)
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        action = page.get_by_role("region", name="Action 1")
        action.get_by_label("Description", exact=True).fill("Unsaved action text")
        page.get_by_label("Overall intention", exact=True).fill("Saved intention")
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_text("Draft revision 3.", exact=False)).to_be_visible()
        expect(action.get_by_label("Description", exact=True)).to_have_value(
            "Unsaved action text"
        )
        page.get_by_role("button", name="Submit turn package", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("Save or discard")
        with world[0].transaction() as session:
            from living_memory.workspace_service import get_draft, package

            saved = package(session, get_draft(session, GAME, "team-0", 1))
            assert saved.overall_intention == "Saved intention"
            assert saved.actions[0].body.description == BODY["description"]
        action.get_by_role("button", name="Save action", exact=True).click()
        expect(page.get_by_text("Draft revision 4.", exact=False)).to_be_visible()
        page.get_by_role("button", name="Submit turn package", exact=True).click()
        expect(page.get_by_text("Effective version 1 · submitted.", exact=True)).to_be_visible()
        browser.close()


def test_typing_during_save_stays_dirty_and_keeps_editor_dom(workspace_server, world):
    from living_memory.workspace_service import get_draft, package

    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                window.fetch = (...args) => original(...args).then(response => {
                    const method = args[1]?.method || "GET";
                    if (method !== "POST") return response;
                    return new Promise(resolve => {
                        window.releaseWorkspaceSave = () => resolve(response);
                    });
                });
                document.querySelector('[data-editor="intention"]').testMarker = "same-node";
            }"""
        )
        intention = page.get_by_label("Overall intention", exact=True)
        intention.fill("Value sent to the server")
        page.get_by_role("button", name="Save intention", exact=True).click()
        page.wait_for_function("window.releaseWorkspaceSave !== undefined")
        intention.fill("Newer text typed during save")
        intention.focus()
        intention.evaluate("node => node.setSelectionRange(6, 10)")
        page.evaluate("window.releaseWorkspaceSave()")
        expect(page.get_by_text("Draft revision 1.", exact=False)).to_be_visible()
        expect(intention).to_have_value("Newer text typed during save")
        expect(page.locator('[data-editor="intention"]')).to_have_attribute("data-dirty", "true")
        assert page.evaluate(
            "document.querySelector('[data-editor=\"intention\"]').testMarker"
        ) == "same-node"
        assert intention.evaluate("node => [node.selectionStart, node.selectionEnd]") == [6, 10]
        with world[0].transaction() as session:
            saved = package(session, get_draft(session, GAME, "team-0", 1))
            assert saved.overall_intention == "Value sent to the server"
        page.get_by_role("link", name="Cancel intention edits", exact=True).click()
        page.get_by_role("button", name="Discard changes", exact=True).click()
        expect(intention).to_have_value("Value sent to the server")
        intention.fill("Drafted after acknowledged save")
        page.reload()
        intention = page.get_by_label("Overall intention", exact=True)
        expect(intention).to_have_value("Drafted after acknowledged save")
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_text("Draft revision 2.", exact=False)).to_be_visible()
        browser.close()


def test_unknown_outcome_retries_frozen_command_once(workspace_server, world):
    from sqlalchemy import func, select

    from living_memory.workspace import PackageRevision
    from living_memory.workspace_service import get_draft, package

    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                let dropped = false;
                window.sentWorkspaceCommands = [];
                window.fetch = (...args) => {
                    if ((args[1]?.method || "GET") !== "POST") return original(...args);
                    window.sentWorkspaceCommands.push(Object.fromEntries(args[1].body));
                    const response = original(...args);
                    if (!dropped) {
                        dropped = true;
                        return response.then(() =>
                            Promise.reject(new TypeError("dropped response"))
                        );
                    }
                    return response;
                };
            }"""
        )
        intention = page.get_by_label("Overall intention", exact=True)
        intention.fill("Frozen original command")
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_role("button", name="Retry save", exact=True)).to_be_visible()
        intention.fill("Later local typing")
        page.locator('[data-editor="intention"]').evaluate(
            "form => { form.action = '/must-not-be-used-for-retry'; }"
        )
        page.get_by_role("button", name="Retry save", exact=True).click()
        expect(page.get_by_text("Draft revision 1.", exact=False)).to_be_visible()
        expect(intention).to_have_value("Later local typing")
        sent = page.evaluate("window.sentWorkspaceCommands")
        assert len(sent) == 2
        for field in ("operation", "key", "expected_version", "overall_intention"):
            assert sent[0][field] == sent[1][field]
        with world[0].transaction() as session:
            draft = get_draft(session, GAME, "team-0", 1)
            assert package(session, draft).overall_intention == "Frozen original command"
            assert session.scalar(
                select(func.count()).select_from(PackageRevision).where(
                    PackageRevision.draft_id == draft.id
                )
            ) == 1
        browser.close()


def test_dirty_editor_keeps_acknowledged_revision_across_teammate_refresh(
    workspace_server, world
):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        editing = page_for(browser, url, tokens, "player", True)
        teammate = page_for(browser, url, tokens, "teammate", True)
        for page in (editing, teammate):
            page.goto(f"{url}/play?game_id={GAME}")
        editing.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                let postHeld = false;
                let refreshHeld = false;
                window.fetch = (...args) => {
                    if ((args[1]?.method || "GET") === "POST" && !postHeld) {
                        postHeld = true;
                        return original(...args).then(response => new Promise(resolve => {
                            window.releaseSave = () => resolve(response);
                        }));
                    }
                    if ((args[1]?.method || "GET") !== "POST" && !refreshHeld) {
                        refreshHeld = true;
                        return new Promise(resolve => {
                            window.releaseRefresh = () => resolve(original(...args));
                        });
                    }
                    return original(...args);
                };
            }"""
        )
        intention = editing.get_by_label("Overall intention", exact=True)
        intention.fill("Acknowledged value")
        editing.get_by_role("button", name="Save intention", exact=True).click()
        editing.wait_for_function("window.releaseSave !== undefined")
        intention.fill("Newer local value")
        editing.evaluate("window.releaseSave()")
        editing.wait_for_function("window.releaseRefresh !== undefined")

        teammate.reload()
        teammate.get_by_label("Overall intention", exact=True).fill("Teammate value")
        teammate.get_by_role("button", name="Save intention", exact=True).click()
        expect(teammate.get_by_text("Draft revision 2.", exact=False)).to_be_visible()
        editing.evaluate("window.releaseRefresh()")
        expect(intention).to_have_value("Newer local value")
        editing.get_by_role("button", name="Save intention", exact=True).click()
        expect(editing.get_by_role("heading", name="Edit conflict", exact=True)).to_be_visible()
        expect(editing.locator("[data-conflict]")).to_contain_text("Teammate value")
        expect(editing.locator("[data-conflict]")).to_contain_text("Newer local value")
        browser.close()


def test_rejected_retry_preserves_original_unknown_command(workspace_server, world):
    from sqlalchemy import func, select

    from living_memory.workspace import PackageRevision

    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                let post = 0;
                window.fetch = (...args) => {
                    if ((args[1]?.method || "GET") !== "POST") return original(...args);
                    post += 1;
                    if (post === 1) return original(...args).then(() =>
                        Promise.reject(new TypeError("dropped response")));
                    if (post === 2) return Promise.resolve(new Response("rejected", {status:403}));
                    return original(...args);
                };
            }"""
        )
        page.get_by_label("Overall intention", exact=True).fill("Committed before rejection")
        page.get_by_role("button", name="Save intention", exact=True).click()
        page.get_by_role("button", name="Retry save", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text(
            "retry was rejected; the original save outcome is still unknown"
        )
        expect(page.get_by_role("button", name="Retry save", exact=True)).to_be_visible()
        expect(page.locator("[data-workspace]")).to_have_attribute("data-unresolved", "true")
        page.get_by_role("button", name="Retry save", exact=True).click()
        expect(page.get_by_text("Draft revision 1.", exact=False)).to_be_visible()
        with world[0].transaction() as session:
            assert session.scalar(select(func.count()).select_from(PackageRevision)) == 1
        browser.close()


def test_discard_uses_latest_authoritative_value_after_scoped_refresh(workspace_server, world):
    from test_workspace import ready

    ready(world)
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        editing = page_for(browser, url, tokens, "player", True)
        teammate = page_for(browser, url, tokens, "teammate", True)
        for page in (editing, teammate):
            page.goto(f"{url}/play?game_id={GAME}")
        edited_action = editing.get_by_role("region", name="Action 1")
        edited_action.get_by_label("Description", exact=True).fill("Unsaved local action")
        teammate_action = teammate.get_by_role("region", name="Action 1")
        teammate_action.get_by_label("Description", exact=True).fill("Newest saved action")
        teammate_action.get_by_role("button", name="Save action", exact=True).click()
        expect(teammate.get_by_text("Draft revision 3.", exact=False)).to_be_visible()
        editing.get_by_label("Overall intention", exact=True).fill("Independent scoped save")
        editing.get_by_role("button", name="Save intention", exact=True).click()
        expect(editing.get_by_text("Draft revision 4.", exact=False)).to_be_visible()
        expect(edited_action.get_by_label("Description", exact=True)).to_have_value(
            "Unsaved local action"
        )
        edited_action.get_by_role("link", name="Cancel action edits", exact=True).click()
        editing.get_by_role("button", name="Discard changes", exact=True).click()
        expect(edited_action.get_by_label("Description", exact=True)).to_have_value(
            "Newest saved action"
        )
        expect(edited_action.locator('form[data-editor^="action-"]')).to_have_attribute(
            "data-dirty", "false"
        )
        browser.close()


@pytest.mark.parametrize("javascript", [False, True])
def test_removed_action_conflict_retains_text_for_recovery(
    workspace_server, world, javascript
):
    from test_workspace import ready

    ready(world)
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        stale = page_for(browser, url, tokens, "player", javascript)
        removing = page_for(browser, url, tokens, "teammate", True)
        stale.goto(f"{url}/play?game_id={GAME}")
        removing.goto(f"{url}/play?game_id={GAME}")
        stale_action = stale.get_by_role("region", name="Action 1")
        if not javascript:
            stale_action.get_by_role("link", name="Edit action", exact=True).click()
            stale_action = stale.get_by_role("region", name="Action 1")
        stale_action.get_by_label("Description", exact=True).fill("Recover removed action text")
        removing.get_by_role("region", name="Action 1").get_by_role(
            "button", name="Remove action", exact=True
        ).click()
        expect(removing.get_by_role("region", name="Action 1")).to_have_count(0)
        stale_action.get_by_role("button", name="Save action", exact=True).click()
        if javascript:
            expect(stale.get_by_role("alert")).to_contain_text("This action was removed")
            recovery = stale.locator("[data-unavailable-recovery]").locator("..").first
            expect(recovery.get_by_label("Description", exact=True)).to_have_value(
                "Recover removed action text"
            )
            expect(stale.get_by_role("button", name="Save mine", exact=True)).to_have_count(0)
        else:
            expect(stale.get_by_role("region", name="Removed action recovery")).to_be_visible()
            expect(stale.locator("[data-conflict]")).to_contain_text(
                "Recover removed action text"
            )
            expect(stale.get_by_role("button", name="Save mine", exact=True)).to_have_count(0)
        browser.close()


def test_committed_save_with_failed_refresh_retries_only_read(workspace_server, world):
    from sqlalchemy import func, select

    from living_memory.workspace import PackageRevision

    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                let failRefresh = true;
                window.postCount = 0;
                window.fetch = (...args) => {
                    if ((args[1]?.method || "GET") === "POST") {
                        window.postCount += 1;
                        return original(...args);
                    }
                    if (failRefresh) {
                        failRefresh = false;
                        return Promise.resolve(new Response("unavailable", {status: 503}));
                    }
                    return original(...args);
                };
            }"""
        )
        page.get_by_label("Overall intention", exact=True).fill("Committed before refresh")
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text(
            "Saved; current view could not be refreshed."
        )
        page.get_by_role("button", name="Submit turn package", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text(
            "Refresh the saved workspace before using a package command."
        )
        assert page.evaluate("window.postCount") == 1
        page.get_by_label("Overall intention", exact=True).fill("Saved after failed refresh")
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_text("Draft revision 2.", exact=False)).to_be_visible()
        assert page.evaluate("window.postCount") == 2
        with world[0].transaction() as session:
            assert session.scalar(select(func.count()).select_from(PackageRevision)) == 2
        browser.close()


def test_unreadable_success_response_remains_uncertain(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                let first = true;
                window.fetch = (...args) => {
                    if ((args[1]?.method || "GET") === "POST" && first) {
                        first = false;
                        return Promise.resolve(new Response("not an acknowledgement", {
                            status: 200, headers: {"Content-Type":"text/html"}
                        }));
                    }
                    return original(...args);
                };
            }"""
        )
        intention = page.get_by_label("Overall intention", exact=True)
        intention.fill("Retained after unreadable response")
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("Save outcome unknown")
        expect(page.get_by_role("button", name="Retry save", exact=True)).to_be_visible()
        expect(intention).to_have_value("Retained after unreadable response")
        browser.close()


def test_acknowledgement_without_committed_revision_remains_uncertain(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                window.fetch = (...args) => {
                    if ((args[1]?.method || "GET") !== "POST") return original(...args);
                    const body = Object.fromEntries(args[1].body);
                    return Promise.resolve(new Response(JSON.stringify({
                        outcome: "committed", operation: body.operation, key: body.key,
                        editor: "intention", refresh: location.href
                    }), {status: 200, headers: {
                        "Content-Type": "application/vnd.living-memory.workspace+json"
                    }}));
                };
            }"""
        )
        page.get_by_label("Overall intention", exact=True).fill("Unverified revision")
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("Save outcome unknown")
        expect(page.get_by_role("button", name="Retry save", exact=True)).to_be_visible()
        browser.close()


def test_access_denied_after_commit_reports_access_change(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                window.fetch = (...args) => (args[1]?.method || "GET") === "POST"
                    ? original(...args)
                    : Promise.resolve(new Response("denied", {status: 403}));
            }"""
        )
        page.get_by_label("Overall intention", exact=True).fill("Committed before access loss")
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("Saved. Your access changed.")
        expect(page.get_by_role("link", name="Go to Home", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Retry refresh", exact=True)).to_have_count(0)
        expect(page.get_by_label("Overall intention", exact=True)).to_have_value(
            "Committed before access loss"
        )
        browser.close()


def test_package_comment_validation_targets_inline_error(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        form = page.locator('[data-editor="package-comment"]')
        form.get_by_label("Comment", exact=True).fill("   ")
        form.get_by_role("button", name="Add package comment", exact=True).click()
        expect(form.locator("#error-package-comment")).to_have_text("Enter a comment")
        browser.close()


def test_confirmed_validation_clears_uncertain_retry(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                let step = 0;
                window.fetch = (...args) => {
                    if ((args[1]?.method || "GET") !== "POST") return original(...args);
                    step += 1;
                    if (step === 1) return Promise.reject(new TypeError("offline"));
                    if (step === 2) return Promise.resolve(new Response(JSON.stringify({
                        outcome:"validation_error",
                        errors:[{field:"overall_intention", message:"Enter an intention."}]
                    }), {status:422, headers:{"Content-Type":"application/json"}}));
                    return original(...args);
                };
            }"""
        )
        intention = page.get_by_label("Overall intention", exact=True)
        intention.fill("Frozen invalid request")
        page.get_by_role("button", name="Save intention", exact=True).click()
        page.get_by_role("button", name="Retry save", exact=True).click()
        expect(page.get_by_role("heading", name="Please check your input")).to_be_visible()
        expect(page.get_by_role("button", name="Save intention", exact=True)).to_be_visible()
        intention.fill("Corrected request")
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_text("Draft revision 1.", exact=False)).to_be_visible()
        browser.close()


def test_use_current_loads_authoritative_conflict_value(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        current = page_for(browser, url, tokens, "player", True)
        stale = page_for(browser, url, tokens, "teammate", True)
        for page in (current, stale):
            page.goto(f"{url}/play?game_id={GAME}")
        current.get_by_label("Overall intention", exact=True).fill("Authoritative value")
        current.get_by_role("button", name="Save intention", exact=True).click()
        expect(current.get_by_text("Draft revision 1.", exact=False)).to_be_visible()
        stale.get_by_label("Overall intention", exact=True).fill("My stale value")
        stale.get_by_role("button", name="Save intention", exact=True).click()
        stale.get_by_role("button", name="Use current", exact=True).click()
        expect(stale.get_by_label("Overall intention", exact=True)).to_have_value(
            "Authoritative value"
        )
        expect(stale.locator('[data-editor="intention"]')).to_have_attribute(
            "data-dirty", "false"
        )
        browser.close()


def test_action_use_current_and_intention_save_combined(workspace_server, world):
    from test_workspace import ready

    ready(world)
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        current = page_for(browser, url, tokens, "player", True)
        stale = page_for(browser, url, tokens, "teammate", True)
        for page in (current, stale):
            page.goto(f"{url}/play?game_id={GAME}")
        current_action = current.get_by_role("region", name="Action 1")
        stale_action = stale.get_by_role("region", name="Action 1")
        current_action.get_by_label("Description", exact=True).fill("Current action text")
        current_action.get_by_role("button", name="Save action", exact=True).click()
        expect(current.get_by_text("Draft revision 3.", exact=False)).to_be_visible()
        stale_action.get_by_label("Description", exact=True).fill("Mine action text")
        stale_action.get_by_role("button", name="Save action", exact=True).click()
        stale_action.get_by_role("button", name="Save combined", exact=True).click()
        expect(stale_action.locator("[data-conflict]")).to_contain_text("Current action text")
        stale_action.get_by_label("Responsible teammate", exact=True).evaluate(
            """select => {
                const option = document.createElement("option");
                option.value = "not-a-uuid"; option.selected = true; select.append(option);
            }"""
        )
        stale_action.get_by_role("button", name="Save action", exact=True).click()
        expect(stale_action.get_by_role("heading", name="Please check your input")).to_be_visible()
        expect(stale_action.locator("[data-conflict]")).to_contain_text("Current action text")
        stale_action.get_by_role("button", name="Use current", exact=True).click()
        expect(stale_action.get_by_label("Description", exact=True)).to_have_value(
            "Current action text"
        )
        expect(stale_action.locator('form[data-editor^="action-"]')).to_have_attribute(
            "data-dirty", "false"
        )

        current.get_by_label("Overall intention", exact=True).fill("Current intention")
        current.get_by_role("button", name="Save intention", exact=True).click()
        expect(current.get_by_text("Draft revision 4.", exact=False)).to_be_visible()
        stale.get_by_label("Overall intention", exact=True).fill("Mine intention")
        stale.get_by_role("button", name="Save intention", exact=True).click()
        stale.get_by_role("button", name="Save combined", exact=True).click()
        expect(stale.get_by_role("status")).to_contain_text("Edit the combined value")
        expect(stale.locator("[data-conflict]")).to_contain_text("Current intention")
        stale.get_by_label("Overall intention", exact=True).fill("Combined intention")
        stale.get_by_role("button", name="Save intention", exact=True).click()
        expect(stale.get_by_text("Draft revision 5.", exact=False)).to_be_visible()
        expect(stale.locator("[data-conflict]")).to_have_count(0)
        browser.close()


def test_package_conflict_requires_review_before_renewal(workspace_server, world):
    from test_workspace import ready

    ready(world)
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        current = page_for(browser, url, tokens, "teammate", True)
        stale = page_for(browser, url, tokens, "player", True)
        for page in (current, stale):
            page.goto(f"{url}/play?game_id={GAME}")
        current.get_by_label("Overall intention", exact=True).fill("Changed package state")
        current.get_by_role("button", name="Save intention", exact=True).click()
        expect(current.get_by_text("Draft revision 3.", exact=False)).to_be_visible()
        stale.get_by_role("button", name="Submit turn package", exact=True).click()
        conflict = stale.locator("[data-conflict]")
        expect(conflict).to_contain_text("Changed package state")
        expect(conflict).to_contain_text("Public initiative")
        stale.get_by_role(
            "button", name="Review current state and renew this operation", exact=True
        ).click()
        expect(stale.get_by_text("Draft revision 3.", exact=False)).to_be_visible()
        expect(stale.get_by_label("Overall intention", exact=True)).to_have_value(
            "Changed package state"
        )
        stale.get_by_role("button", name="Submit turn package", exact=True).click()
        expect(stale.get_by_text("Effective version 1 · submitted.", exact=True)).to_be_visible()
        browser.close()


def test_removed_dirty_action_retains_copy_discard_recovery(workspace_server, world):
    from test_workspace import ready

    ready(world)
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        editing = page_for(browser, url, tokens, "player", True)
        removing = page_for(browser, url, tokens, "teammate", True)
        for page in (editing, removing):
            page.goto(f"{url}/play?game_id={GAME}")
        action = editing.get_by_role("region", name="Action 1")
        action.get_by_label("Description", exact=True).fill("Text to recover")
        removing.get_by_role("region", name="Action 1").get_by_role(
            "button", name="Remove action", exact=True
        ).click()
        expect(removing.get_by_role("region", name="Action 1")).to_have_count(0)
        expect(action.get_by_label("Description", exact=True)).to_have_value("Text to recover")
        editing.get_by_label("Overall intention", exact=True).fill("Trigger scoped refresh")
        editing.get_by_role("button", name="Save intention", exact=True).click()
        expect(
            editing.get_by_text("This editor is no longer available.", exact=False)
        ).to_be_visible()
        recovery = editing.locator("[data-unavailable-recovery]").locator("..").first
        expect(recovery.get_by_label("Description", exact=True)).to_have_value("Text to recover")
        expect(recovery.get_by_label("Description", exact=True)).to_be_disabled()
        expect(editing.get_by_role("button", name="Copy retained text", exact=True)).to_be_visible()
        editing.evaluate(
            """Object.defineProperty(navigator, "clipboard", {
                configurable: true,
                value: {writeText: () => Promise.reject(new Error("blocked"))}
            })"""
        )
        editing.get_by_role("button", name="Copy retained text", exact=True).click()
        manual = editing.get_by_label("Retained text for manual copy", exact=True)
        expect(manual).to_be_visible()
        expect(manual).to_be_focused()
        expect(manual).to_have_value(re.compile("Text to recover"))
        discard = editing.get_by_role("button", name="Discard retained text", exact=True)
        expect(discard).to_be_visible()
        discard.click()
        expect(editing.locator("[data-unavailable-recovery]")).to_have_count(0)
        expect(editing.get_by_role("heading", name="New action", exact=True)).to_be_visible()
        browser.close()


def test_second_reorder_is_blocked_while_first_mutation_is_in_flight(workspace_server, world):
    from test_workspace import BODY, ready, run

    ready(world)
    run(world, "action", body={**BODY, "title": "Second action"})
    run(world, "action", body={**BODY, "title": "Third action"})
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                window.reorderPosts = 0;
                window.fetch = (...args) => {
                    if ((args[1]?.method || "GET") !== "POST") return original(...args);
                    window.reorderPosts += 1;
                    const response = original(...args);
                    if (window.reorderPosts === 1) {
                        return response.then(value => new Promise(resolve => {
                            window.releaseReorder = () => resolve(value);
                        }));
                    }
                    return response;
                };
            }"""
        )
        moves = page.get_by_role("button", name="Move up", exact=True)
        expect(moves).to_have_count(2)
        moves.nth(0).click()
        page.wait_for_function("window.releaseReorder !== undefined")
        moves.nth(1).click()
        expect(page.get_by_role("alert")).to_contain_text("Wait for the current save")
        assert page.evaluate("window.reorderPosts") == 1
        page.evaluate("window.releaseReorder()")
        expect(page.get_by_text("Action order updated.", exact=True)).to_be_visible()
        browser.close()


def test_decision_conflict_refreshes_current_state_and_retains_reason(workspace_server, world):
    from test_workspace import ready, run

    ready(world)
    run(world, "submit")
    run(world, "intention", overall_intention="Amended intention")
    run(world, "amend", effective_version=1)
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        current = page_for(browser, url, tokens, "judge", True)
        stale = page_for(browser, url, tokens, "judge", True)
        for page in (current, stale):
            page.goto(f"{url}/adjudicate?game_id={GAME}")
        current.get_by_label("Reason", exact=True).fill("Accept current amendment")
        current.get_by_role("button", name="Record amendment decision", exact=True).click()
        expect(current.get_by_text("Effective version 2 · submitted.", exact=True)).to_be_visible()
        stale.get_by_label("Decision", exact=True).select_option("rejected")
        stale.get_by_label("Reason", exact=True).fill("Retain this stale reason")
        stale.get_by_role("button", name="Record amendment decision", exact=True).click()
        expect(stale.locator("[data-conflict]")).to_contain_text("accepted")
        stale.get_by_role(
            "button", name="Review current state and renew this operation", exact=True
        ).click()
        expect(stale.get_by_text("Effective version 2 · submitted.", exact=True)).to_be_visible()
        recovery = stale.locator("[data-unavailable-recovery]").locator("..").first
        expect(recovery.get_by_label("Reason", exact=True)).to_have_value(
            "Retain this stale reason"
        )
        expect(
            recovery.get_by_role("button", name="Discard retained text", exact=True)
        ).to_be_visible()
        browser.close()


def test_confirmed_rejection_and_keyboard_cancel(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        intention = page.get_by_label("Overall intention", exact=True)
        intention.fill("Retained after rejection")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                window.fetch = (...args) => (args[1]?.method || "GET") === "POST"
                    ? Promise.resolve(new Response(JSON.stringify({outcome:"rejected"}), {
                        status: 403, headers: {"Content-Type":"application/json"}
                    }))
                    : original(...args);
            }"""
        )
        page.get_by_role("button", name="Save intention", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("Save was rejected")
        expect(page.get_by_role("alert")).not_to_contain_text("unknown")
        assert page.locator("[data-workspace]").get_attribute("data-unresolved") != "true"
        expect(intention).to_have_value("Retained after rejection")

        cancel = page.get_by_role("link", name="Cancel intention edits", exact=True)
        cancel.focus()
        page.keyboard.press("Enter")
        expect(page.get_by_role("alertdialog", name="Unsaved changes")).to_be_visible()
        page.keyboard.press("Escape")
        expect(cancel).to_be_focused()
        page.keyboard.press("Enter")
        page.get_by_role("button", name="Discard changes", exact=True).click()
        expect(intention).to_have_value("")
        browser.close()


def test_reload_restores_dirty_text_without_replay_or_cross_user_leak(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        posts = []
        page.on(
            "request",
            lambda request: posts.append(request.url) if request.method == "POST" else None,
        )
        page.goto(f"{url}/play?game_id={GAME}")
        page.get_by_label("Overall intention", exact=True).fill("Recover after reload")
        page.reload()
        expect(page.get_by_label("Overall intention", exact=True)).to_have_value(
            "Recover after reload"
        )
        assert posts == []

        context = page.context
        context.clear_cookies()
        context.add_cookies([dict(name="lm_auth", value=tokens["teammate"], url=url)])
        page.goto(f"{url}/play?game_id={GAME}")
        expect(page.get_by_label("Overall intention", exact=True)).to_have_value("")
        assert posts == []
        browser.close()


def test_navigation_discard_clears_workspace_recovery_text(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.get_by_label("Overall intention", exact=True).fill("Discard before leaving")
        page.get_by_role("link", name="Living Memory", exact=True).click()
        page.get_by_role("button", name="Discard changes", exact=True).click()
        expect(page).to_have_url(f"{url}/")
        page.get_by_role("link", name="Team 0 workspace · submitter", exact=True).click()
        expect(page.get_by_label("Overall intention", exact=True)).to_have_value("")
        browser.close()


def test_blocked_session_storage_keeps_in_page_draft(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        context.add_cookies([dict(name="lm_auth", value=tokens["player"], url=url)])
        context.add_init_script(
            """for (const method of ["getItem", "setItem", "removeItem", "key"]) {
                Object.defineProperty(Storage.prototype, method, {
                    value() { throw new DOMException("blocked", "SecurityError"); }
                });
            }"""
        )
        page = context.new_page()
        page.goto(f"{url}/play?game_id={GAME}")
        intention = page.get_by_label("Overall intention", exact=True)
        intention.fill("Kept in memory")
        expect(
            page.get_by_text("Draft recovery is available only while this page remains open.")
        ).to_be_visible()
        expect(intention).to_have_value("Kept in memory")
        expect(page.locator('[data-editor="intention"]')).to_have_attribute("data-dirty", "true")
        browser.close()


def test_admin_dirty_form_guards_shell_navigation(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "admin", True)
        page.goto(f"{url}/admin")
        page.get_by_text("Create local user", exact=True).click()
        form = page.locator('form[action="/admin/users"]')
        username = form.get_by_label("Username", exact=True)
        username.fill("unfinished-admin-input")
        expect(form).to_have_attribute("data-dirty", "true")
        home = page.get_by_role("link", name="Living Memory", exact=True)
        home.click()
        dialog = page.get_by_role("alertdialog", name="Unsaved changes")
        expect(dialog).to_be_visible()
        dialog.get_by_role("button", name="Keep editing", exact=True).click()
        expect(username).to_have_value("unfinished-admin-input")
        home.click()
        dialog.get_by_role("button", name="Discard changes", exact=True).click()
        expect(page).to_have_url(f"{url}/")
        browser.close()


def test_unknown_package_command_restores_after_reload(workspace_server, world):
    from sqlalchemy import func, select
    from test_workspace import ready

    from living_memory.workspace import SubmissionVersion

    ready(world)
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                let dropped = false;
                window.fetch = (...args) => {
                    if ((args[1]?.method || "GET") !== "POST" || dropped) return original(...args);
                    dropped = true;
                    return original(...args).then(() => Promise.reject(new TypeError("dropped")));
                };
            }"""
        )
        page.get_by_role("button", name="Submit turn package", exact=True).click()
        expect(page.get_by_role("button", name="Retry save", exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_text("A previous submit has an unknown outcome.")).to_be_visible()
        page.get_by_label("Overall intention", exact=True).fill("Unsaved text after submit")
        page.locator("[data-workspace]").evaluate(
            "workspace => { workspace.dataset.refreshPending = 'true'; }"
        )
        page.get_by_role("button", name="Retry original operation", exact=True).click()
        expect(page.get_by_text("Effective version 1 · submitted.", exact=True)).to_be_visible()
        expect(page.get_by_label("Overall intention", exact=True)).to_have_value(
            "Unsaved text after submit"
        )
        with world[0].transaction() as session:
            assert session.scalar(select(func.count()).select_from(SubmissionVersion)) == 1
        browser.close()


def test_orphaned_operation_name_is_rendered_as_text(workspace_server):
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const prefix = `lm-workspace:${document.body.dataset.userId}:${
                    document.querySelector('[data-workspace]').dataset.workspace}`;
                const frozen = {
                    operation: '<img src=x onerror="window.orphanInjected=true">',
                    action: '/never-submit', values: {}
                };
                sessionStorage.setItem(`${prefix}:unresolved-command`, JSON.stringify({
                    state: `${prefix}:missing:pending`, frozen
                }));
            }"""
        )
        page.reload()
        expect(page.get_by_text("A previous <img src=x", exact=False)).to_be_visible()
        expect(page.locator("[data-pending-recovery] img")).to_have_count(0)
        assert page.evaluate("window.orphanInjected") is None
        browser.close()


def test_new_action_receives_stable_identity_and_clears_creator(workspace_server, world):
    from sqlalchemy import func, select

    from living_memory.workspace import DraftAction

    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                let gated = false;
                window.fetch = (...args) => original(...args).then(response => {
                    if ((args[1]?.method || "GET") !== "POST" || gated) return response;
                    gated = true;
                    return new Promise(resolve => {
                        window.releaseNewActionSave = () => resolve(response);
                    });
                });
            }"""
        )
        creator = page.locator('[data-editor="new-action"]')
        creator.get_by_label("Title", exact=True).fill("Created once")
        creator.get_by_label("Description", exact=True).fill("Initial description")
        creator.get_by_label("Intent of Action", exact=True).fill("Initial intent")
        creator.get_by_label("Anticipated reaction", exact=True).fill("Initial reaction")
        creator.get_by_role("button", name="Add action", exact=True).click()
        page.wait_for_function("window.releaseNewActionSave !== undefined")
        creator.get_by_label("Description", exact=True).fill("Updated during create")
        page.evaluate("window.releaseNewActionSave()")
        action = page.get_by_role("region", name="Action 1")
        expect(action.get_by_role("heading", name="Action 1: Created once")).to_be_visible()
        expect(
            page.locator('[data-editor="new-action"]').get_by_label("Title", exact=True)
        ).to_have_value("")
        stable_editor = action.locator('form[data-editor^="action-"]')
        expect(stable_editor).to_have_count(1)
        expect(stable_editor.get_by_label("Description", exact=True)).to_have_value(
            "Updated during create"
        )
        expect(stable_editor).to_have_attribute("data-dirty", "true")
        stable_editor.get_by_label("Description", exact=True).fill("Updated description")
        stable_editor.get_by_role("button", name="Save action", exact=True).click()
        expect(action.get_by_text("Updated description", exact=True)).to_be_visible()
        with world[0].transaction() as session:
            assert session.scalar(select(func.count()).select_from(DraftAction)) == 1
        browser.close()


def test_unknown_new_action_retry_creates_one_durable_action(workspace_server, world):
    from sqlalchemy import func, select

    from living_memory.workspace import DraftAction

    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                let dropped = false;
                window.fetch = (...args) => {
                    if ((args[1]?.method || "GET") !== "POST" || dropped) return original(...args);
                    dropped = true;
                    return original(...args).then(() => Promise.reject(new TypeError("dropped")));
                };
            }"""
        )
        creator = page.locator('[data-editor="new-action"]')
        creator.get_by_label("Title", exact=True).fill("Exactly once action")
        creator.get_by_label("Description", exact=True).fill("Durable description")
        creator.get_by_label("Intent of Action", exact=True).fill("Durable intent")
        creator.get_by_label("Anticipated reaction", exact=True).fill("Durable reaction")
        creator.get_by_role("button", name="Add action", exact=True).click()
        creator.get_by_role("button", name="Retry save", exact=True).click()
        expect(page.get_by_role("heading", name="Action 1: Exactly once action")).to_be_visible()
        with world[0].transaction() as session:
            assert session.scalar(select(func.count()).select_from(DraftAction)) == 1
        browser.close()


def test_unknown_comment_retry_creates_one_durable_comment(workspace_server, world):
    from sqlalchemy import func, select
    from test_workspace import ready

    from living_memory.workspace import DraftComment

    ready(world)
    url, tokens = workspace_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = page_for(browser, url, tokens, "player", True)
        page.goto(f"{url}/play?game_id={GAME}")
        page.evaluate(
            """() => {
                const original = window.fetch.bind(window);
                let dropped = false;
                window.fetch = (...args) => {
                    if ((args[1]?.method || "GET") !== "POST" || dropped) return original(...args);
                    dropped = true;
                    return original(...args).then(() => Promise.reject(new TypeError("dropped")));
                };
            }"""
        )
        action = page.get_by_role("region", name="Action 1")
        comment = action.locator('form[data-editor^="comment-"]')
        comment.get_by_role("textbox", name="Action comment").fill("Exactly once comment")
        comment.get_by_role("button", name="Add action comment", exact=True).click()
        comment.get_by_role("button", name="Retry save", exact=True).click()
        expect(page.get_by_text("Exactly once comment", exact=True)).to_be_visible()
        with world[0].transaction() as session:
            assert session.scalar(select(func.count()).select_from(DraftComment)) == 1
        browser.close()
