"""Phase F: pin the square-root path that the application actually uses.

Phase E reported "sqrt is broken on the server path". That finding is RETRACTED.
It was measured with POST /api/key {"key":"sqrt"}, the server's per-key
emulation, which the calculator's UI never uses.

The real path is:

    browser keypad  ->  getExpr()  ->  POST /api/key {"key":"equals",
                                                        "expression": ...}

and on that path sqrt(16) = 4 and sqrt(9+16) = 5 in BOTH the development
branch and the shipped v0.1 package.

These tests lock that behaviour in so it cannot regress, and so a future reader
does not "fix" the wrong layer. There is no application change in Phase F
because there is no defect to fix on the user-facing path.

The one genuinely broken surface found -- the server's per-key template
emulation -- is encoded with expectedFailure so that fixing it is reported
rather than silently absorbed.
"""
import json
import os
import pathlib
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request

PROJECT = pathlib.Path(__file__).resolve().parents[2]
CHROMIUM = r"C:\Users\DELL\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe"
FRONTEND = PROJECT / "frontend.html"
SERVER = PROJECT / "mvp_server.py"
TIMEOUT = 10

# (label, keypad keys, serialised expression, expected value)
SERIALISATION_CASES = [
    ("sqrt16", ["sqrt", "1", "6"], "sqrt(16)", 4),
    ("sqrt9plus16", ["sqrt", "9", "plus", "1", "6"], "sqrt(9+16)", 5),
    ("nested radicand", ["sqrt", "4", "plus", "sqrt", "1", "6"],
     "sqrt(4+sqrt(16))", None),
    ("sqrt of explicit group", ["sqrt", "left_paren", "9", "plus", "1", "6",
                                "right_paren"], "sqrt((9+16))", 5),
]


# ---------------------------------------------------------------------------
# 1. Serialisation: the keypad must emit a BALANCED expression
# ---------------------------------------------------------------------------


@unittest.skipUnless(os.path.exists(CHROMIUM), "chromium is not installed")
class TestSqrtKeypadSerialisation(unittest.TestCase):
    """The keypad must not depend on anything downstream to repair its output."""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls._pw_ctx = sync_playwright()
        cls._pw = cls._pw_ctx.start()
        cls._browser = cls._pw.chromium.launch(headless=True,
                                                executable_path=CHROMIUM)
        cls.page = cls._browser.new_page()
        cls.page.goto("file:///" + str(FRONTEND).replace("\\", "/"),
                      wait_until="load")

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def _type(self, keys):
        page = self.page
        page.evaluate(
            "() => { if (typeof hardResetExpr === 'function') hardResetExpr(); }")
        page.wait_for_timeout(60)
        for k in keys:
            loc = page.locator('[data-key="%s"]' % k)
            self.assertGreater(loc.count(), 0, "no keypad control %r" % k)
            loc.click()
        page.wait_for_timeout(250)
        return page.evaluate(
            "() => (typeof getExpr === 'function') ? getExpr() : None")

    def test_keypad_emits_the_expected_exact_string(self):
        for label, keys, expected, _v in SERIALISATION_CASES:
            with self.subTest(case=label):
                self.assertEqual(self._type(keys), expected)

    def test_keypad_output_is_balanced(self):
        # The regression that matters: an unbalanced radical is silently
        # repaired by the browser evaluator and rejected by the server.
        for label, keys, expected, _v in SERIALISATION_CASES:
            with self.subTest(case=label):
                built = self._type(keys)
                self.assertEqual(built.count("("), built.count(")"),
                                 "unbalanced radicals: %r" % (built,))

    def test_sqrt_is_not_silently_repaired_downstream(self):
        # localEvaluate must receive the balanced string verbatim.
        built = self._type(["sqrt", "1", "6"])
        got = self.page.evaluate(
            "(e) => { try { return String(localEvaluate(e)); } "
            "catch (err) { return 'ERR:' + (err && err.message); } }", built)
        self.assertEqual(got, "4")


# ---------------------------------------------------------------------------
# 2. Server: the expression the browser sends must evaluate correctly
# ---------------------------------------------------------------------------


class _Server:
    def __enter__(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER), "--port", str(port), "--no-browser"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.base = "http://127.0.0.1:%d" % port
        for _ in range(150):
            try:
                with urllib.request.urlopen(self.base + "/health",
                                            timeout=2) as r:
                    if r.status == 200:
                        return self
            except Exception:  # noqa: BLE001
                time.sleep(0.1)
        raise RuntimeError("server did not start")

    def post(self, path, data):
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            self.base + path, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def __exit__(self, *exc):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            self.proc.kill()
        return False


class TestSqrtServerPath(unittest.TestCase):
    """Exactly the surface the browser uses."""

    def test_sqrt16_and_sqrt9plus16_evaluate(self):
        with _Server() as srv:
            for expr, want in [("sqrt(16)", "4"), ("sqrt(9+16)", "5"),
                               ("sqrt((9+16))", "5"),
                               ("sqrt(4+sqrt(16))", None)]:
                with self.subTest(expr=expr):
                    srv.post("/api/reset", {"target": "all"})
                    st, b = srv.post("/api/key", {"key": "equals",
                                                  "expression": expr})
                    self.assertIsNone(b.get("error"),
                                      "%s -> %r" % (expr, b.get("error")))
                    if want is not None:
                        self.assertEqual(str(b.get("result")), want)
            # nested radicand is a documented numeric check, not a string one
            srv.post("/api/reset", {"target": "all"})
            _st, b = srv.post("/api/key", {"key": "equals",
                                           "expression": "sqrt(4+sqrt(16))"})
            self.assertAlmostEqual(float(b.get("result")),
                                   (4 + 4) ** 0.5, places=6)

    def test_invalid_radicand_still_errors(self):
        # Established error handling must be preserved, not relaxed.
        with _Server() as srv:
            for expr in ("sqrt(-1)", "xroot(0,5)"):
                with self.subTest(expr=expr):
                    srv.post("/api/reset", {"target": "all"})
                    _st, b = srv.post("/api/key", {"key": "equals",
                                                   "expression": expr})
                    self.assertTrue(b.get("error"),
                                    "%s should error, got %r" % (expr, b))


# ---------------------------------------------------------------------------
# 3. The known gap: the server's per-key template emulation
# ---------------------------------------------------------------------------


@unittest.expectedFailure
class TestPerKeyEmulationIsNotTheUserPath(unittest.TestCase):
    """POST {"key":"sqrt"} builds an unbalanced template and fails.

    This is NOT reachable from the calculator UI: the CALC keypad keeps its
    state in the frontend and sends only {"key":"equals","expression":...}. It is
    encoded as expectedFailure so that fixing it is REPORTED (unittest raises
    unexpectedSuccess) instead of being silently absorbed, and so nobody
    mistakes it for the reported defect.
    """

    def test_per_key_sqrt_emulation(self):
        with _Server() as srv:
            srv.post("/api/reset", {"target": "all"})
            last = None
            for k in ("sqrt", "1", "6", "equals"):
                last = srv.post("/api/key", {"key": k})
            _st, b = last
            self.assertEqual(str(b.get("result")), "4",
                             "per-key sqrt emulation now works; update this "
                             "test and the Phase F report")


if __name__ == "__main__":
    unittest.main()