import json
import socket
import threading
import time
from urllib.parse import urlencode, urlsplit

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright
from test_database import database  # noqa: F401
from test_memory import timeline  # noqa: F401

from living_memory.app import create_app
from living_memory.db import ROOT

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
