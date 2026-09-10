import socket
import threading
import time
from urllib.parse import urlsplit

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

from living_memory.app import create_app

pytestmark = pytest.mark.browser


@pytest.fixture
def server(settings):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    config = uvicorn.Config(create_app(settings), log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                pytest.fail("Browser server did not start")
            time.sleep(0.01)
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


@pytest.mark.parametrize("javascript", [True, False])
def test_keyboard_forms_and_local_assets(server, javascript):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(java_script_enabled=javascript)
        page = context.new_page()
        page.set_default_timeout(10000)
        external = []
        page.on(
            "request",
            lambda request: (
                external.append(request.url)
                if urlsplit(request.url).netloc != urlsplit(server).netloc
                else None
            ),
        )
        page.goto(server)
        page.keyboard.press("Tab")
        expect(page.get_by_role("link", name="Skip to main content")).to_be_focused()
        page.get_by_role("link", name="Try the form demonstration").click()
        if javascript:
            page.wait_for_function("window.htmx !== undefined")
        page.get_by_label("Title", exact=True).fill("")
        page.get_by_label("Action 1", exact=True).fill("first\nline")
        page.get_by_label("Action 2", exact=True).fill("second")
        with page.expect_response(lambda response: response.request.method == "POST") as response:
            page.get_by_role("button", name="Submit demonstration").click()
        assert response.value.status == 422
        expect(page.get_by_role("alert")).to_be_visible()
        expect(page.get_by_label("Action 1", exact=True)).to_have_value("first\nline")
        expect(page.get_by_label("Action 2", exact=True)).to_have_value("second")
        page.get_by_label("Title", exact=True).fill("Valid")
        page.get_by_role("button", name="Submit demonstration").focus()
        page.keyboard.press("Enter")
        expect(page.get_by_role("status")).to_contain_text("Form accepted.")
        page.reload()
        expect(page.get_by_role("status")).to_have_count(0)
        assert external == []
        browser.close()


def test_htmx_conflict_swap_and_csrf(server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(server + "/dev/forms")
        page.wait_for_function("window.htmx !== undefined")
        page.route(
            "**/dev/forms",
            lambda route: (
                route.fulfill(
                    status=409,
                    content_type="text/html",
                    body='<form id="demo-form"><p role="alert">Recoverable conflict</p></form>',
                )
                if route.request.method == "POST"
                else route.continue_()
            ),
        )
        page.get_by_role("button", name="Submit demonstration").click()
        expect(page.get_by_role("alert")).to_have_text("Recoverable conflict")
        page.unroute("**/dev/forms")
        page.reload()
        page.locator('[name="csrf_token"]').evaluate("(element) => element.value = 'wrong'")
        with page.expect_response(lambda response: response.request.method == "POST") as response:
            page.get_by_role("button", name="Submit demonstration").click()
        assert response.value.status == 403
        browser.close()
