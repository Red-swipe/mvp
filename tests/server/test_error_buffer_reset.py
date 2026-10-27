"""Regression: a failed calculation must not survive into the next one.

Defect (found by audit/tools/ans_sequences.py, Phase D commit d04aad0, confirmed
again in Phase E):

    server:  10 =          -> ans = 10
             1 / 0 =       -> HTTP 400, state ERROR, but the expression buffer
                               still holds "1/0"
             Ans + 1 =     -> evaluates "1/010+1" and returns 1.1

    browser: same sequence  -> 1/0 shows Math ERROR, then Ans+1 = 11

The frontend already does the right thing: normalizeResultErrorEntry()
(frontend.html) calls resetExpr() whenever appState.error is set, preserving
lastAnswer. The server had no equivalent, so a failed calculation's text leaked
into the next one and silently produced a wrong number with no error shown.

Contract this test pins (audit/docs/decision_record_errors.md):
  - divide by zero is a CALCULATION error, never a system error
  - Ans is preserved through the error
  - the next calculation starts from a clean buffer
  - the calculator stays usable afterwards

It deliberately does NOT assert a div-by-zero display string or an HTTP status:
those remain blocked by Gate B. It asserts the error is reported and that no
stale text survives.
"""
import pathlib
import sys

import pytest

PROJECT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))

CHROMIUM = r"C:\Users\DELL\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"


# ---------------------------------------------------------------------------
# Server path: real HTTP against the real mvp_server.py
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_post():
    import json
    import socket
    import subprocess
    import time
    import urllib.error
    import urllib.request

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, str(PROJECT / "mvp_server.py"), "--port", str(port),
         "--no-browser"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % port
    try:
        for _ in range(150):
            try:
                with urllib.request.urlopen(base + "/health", timeout=2) as r:
                    if r.status == 200:
                        break
            except Exception:  # noqa: BLE001
                time.sleep(0.1)
        else:
            pytest.fail("test server did not start")

        def post(path_, data):
            body = json.dumps(data).encode()
            req = urllib.request.Request(
                base + path_, data=body,
                headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read())

        yield post
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            proc.kill()


def _keys(post_fn, *keys):
    last = None
    for k in keys:
        last = post_fn("/api/key", {"key": k})
    return last


def test_divzero_reports_a_calculation_error(live_post):
    live_post("/api/reset", {"target": "all"})
    _, body = _keys(live_post, "1", "divide", "0", "equals")
    # The error is reported one way or another; what matters is that it is an
    # error and that the state says so. The exact string and HTTP status stay
    # blocked by Gate B and are deliberately not asserted here.
    assert body.get("state") == "ERROR" or body.get("error"), body


def test_failed_expression_does_not_survive_into_the_next_calculation(live_post):
    """The core regression: Ans+1 must be 11, not 1.1."""
    live_post("/api/reset", {"target": "all"})

    # 1. establish Ans = 10
    _keys(live_post, "1", "0", "equals")
    _, body = _keys(live_post, "equals")
    assert str(body.get("ans")) == "10", body

    # 2. divide by zero -> a calculation error
    _, body = _keys(live_post, "1", "divide", "0", "equals")
    assert body.get("state") == "ERROR" or body.get("error"), body

    # 3. Ans is preserved through the failure
    assert str(body.get("ans")) == "10", \
        "Ans must survive a calculation error, got %r" % (body.get("ans"),)

    # 4. a fresh Ans+1 must start from a CLEAN buffer
    _, body = _keys(live_post, "ans", "plus", "1", "equals")
    assert str(body.get("result")) == "11", (
        "the failed expression leaked into the next calculation: "
        "expression=%r result=%r (expected 11)"
        % (body.get("expression"), body.get("result")))


def test_no_residual_text_after_the_error(live_post):
    live_post("/api/reset", {"target": "all"})
    _keys(live_post, "1", "divide", "0", "equals")
    _, body = _keys(live_post, "ans", "plus", "1", "equals")
    assert "1/0" not in str(body.get("expression")), \
        "stale expression text survived: %r" % (body.get("expression"),)


def test_calculator_remains_usable_after_a_calculation_error(live_post):
    live_post("/api/reset", {"target": "all"})
    _keys(live_post, "1", "divide", "0", "equals")
    _, body = _keys(live_post, "2", "plus", "2", "equals")
    assert str(body.get("result")) == "4", \
        "the calculator did not recover: %r" % (body.get("result"),)


# ---------------------------------------------------------------------------
# Browser path: the same sequence, real keypad, real chromium
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not pathlib.Path(CHROMIUM).exists(),
                    reason="chromium is not installed")
def test_frontend_keeps_the_failed_expression_out_of_the_next_input():
    """The served page must not carry a failed expression into the next one.

    Retargeted from file:// to the SERVED page. file:// is not a supported
    deployment mode: there the DIV_ZERO result branch is taken and
    appState.error legitimately stays null, so the old assertion could not
    hold. On the served page (FILE_MODE false) evaluate() takes the fetch()
    path, a genuine calculation error sets appState.error, and the buffer
    reset contract is what we actually want to pin.
    """
    import json
    import socket
    import subprocess
    import threading
    import time
    from http.server import ThreadingHTTPServer
    from playwright.sync_api import sync_playwright

    import mvp_server  # noqa: E402

    srv = ThreadingHTTPServer(("127.0.0.1", 0), mvp_server.MvpHandler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.4)
    browser = None
    pw = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page()
        page.goto("http://127.0.0.1:%d/" % port, wait_until="load")
        page.wait_for_timeout(1200)
        assert page.evaluate(
            "() => (typeof FILE_MODE !== 'undefined') ? FILE_MODE : true"
        ) is False, "this test must run against the served page, not file://"

        page.evaluate("() => { hardResetExpr(); appState.shift = false; }")
        for k in ["1", "0", "equals"]:
            page.locator('[data-key="%s"]' % k).click()
        page.wait_for_timeout(500)
        ans_after_ten = page.evaluate("() => appState.lastAnswer")

        for k in ["1", "divide", "0", "equals"]:
            page.locator('[data-key="%s"]' % k).click()
        page.wait_for_timeout(700)
        assert page.evaluate("() => !!appState.error"), \
            "1/0 must raise a calculation error on the served page"

        # Ans survives the error
        assert str(page.evaluate("() => appState.lastAnswer")) == str(ans_after_ten), \
            "the frontend lost Ans across an error"

        # the next input starts clean
        for k in ["ans", "plus", "1", "equals"]:
            page.locator('[data-key="%s"]' % k).click()
        page.wait_for_timeout(700)
        assert page.evaluate("() => getExpr()") == "Ans+1", \
            "frontend built %r instead of a fresh Ans+1" % (
                page.evaluate("() => getExpr()"),)
        assert str(page.evaluate("() => appState.result")) == "11", \
            "frontend returned %r, expected 11" % (
                page.evaluate("() => appState.result"),)
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if pw is not None:
            try:
                pw.stop()
            except Exception:
                pass
        srv.shutdown()
        srv.server_close()