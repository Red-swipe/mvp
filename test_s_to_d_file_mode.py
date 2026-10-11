"""Item 3 regression coverage: S<->D under file:// must produce the EXACT
fraction, and must agree with the served /api/fraction path.

Defect this locks down: the file:// branch of toggleAnswerFormat() called
fractionString(), which pins the denominator at 1000. So pressing S<->D on
1/3 showed the misleading `333/1000` instead of `1/3`. It also silently
corrupted state further than the LCD: the next S<->D press read the corrupted
`333/1000` back as a number and printed `0.333`, losing the original
`0.3333333333` for good.

The served path asks /api/fraction, which uses
Fraction(value).limit_denominator(10000). limitFraction() in frontend.html is
that same continued-fraction search, so the two paths must agree value for
value. Both are asserted here, on the real rendered app.

Static layer: the helper is wired and the buggy helper is no longer used.
Browser layer: file:// and http:// round trips, checking appState.result AND
appState.lastAnswer so a correct-looking LCD cannot hide a corrupted value.
"""
import json
import pathlib
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

FRONTEND_PATH = pathlib.Path(__file__).resolve().parent / "frontend.html"
FRONTEND = FRONTEND_PATH.read_text(encoding="utf-8")

try:
    from playwright.sync_api import sync_playwright

    _pw = sync_playwright().start()
    _b = _pw.chromium.launch(channel="chrome")
    HAVE_BROWSER = True
    _b.close()
    _pw.stop()
except Exception:  # pragma: no cover - environment dependent
    HAVE_BROWSER = False

# Each case is (expression, exact fraction, decimal it must return to). The
# expressions are typed character by character, the same way test_output_modes
# drives the engine, so this goes through the real token path.
ROUND_TRIP = [
    ("1/3", "1/3", "0.3333333333"),
    ("2/3", "2/3", "0.6666666667"),
    ("7/3", "7/3", "2.333333333"),
    ("1/7", "1/7", "0.1428571429"),
]


class TestFractionHelperWiring(unittest.TestCase):
    def test_helper_exists(self):
        self.assertIn("function limitFraction(", FRONTEND)
        self.assertIn("function exactFractionString(", FRONTEND)

    def test_toggle_uses_the_exact_helper_in_file_mode(self):
        body = FRONTEND[FRONTEND.index("async function toggleAnswerFormat("):]
        body = body[: body.index("const DIV_ZERO_MSG")]
        file_branch = body[body.index("if (FILE_MODE) {"):]
        file_branch = file_branch[: file_branch.index("} else {")]
        self.assertIn("exactFractionString(", file_branch)

    def test_the_thousand_denominator_helper_is_no_longer_used(self):
        # fractionString() stays defined for reference, but the S<->D path
        # must never call it: it is what produced 333/1000.
        body = FRONTEND[FRONTEND.index("async function toggleAnswerFormat("):]
        body = body[: body.index("const DIV_ZERO_MSG")]
        self.assertNotIn("fractionString(", body)

    def test_denominator_is_bounded_like_the_server(self):
        fn = FRONTEND[FRONTEND.index("function exactFractionString("):]
        fn = fn[: fn.index("function exactSolveFormat(")]
        self.assertIn("limitFraction(value, 10000)", fn)

    def test_exact_solve_format_is_left_intact(self):
        # exactSolveFormat() backs SOLVE/EQN. It must keep its own
        # continued-fraction test rather than being redirected at limitFraction.
        fn = FRONTEND[FRONTEND.index("function exactSolveFormat("):]
        fn = fn[: fn.index("async function toggleAnswerFormat(")]
        self.assertIn("Math.abs(candidate - value) < 1e-9", fn)


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class SToDBase(unittest.TestCase):
    """Drives S<->D through the real function and reads the real state."""

    def make_page(self, url):
        page = self.browser.new_page(viewport={"width": 1000, "height": 1300})
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        return page

    def type_expression(self, page, expr):
        page.evaluate(
            """(e) => { resetExpr();
                 appState.result = null; appState.resultDisplayed = false;
                 for (const c of e) insertToken(c);
                 evaluate(); }""",
            expr)
        # evaluate() is async (over http:// it posts to the backend), so wait
        # for the state to actually land instead of guessing with a sleep.
        page.wait_for_function(
            "() => appState.resultDisplayed && appState.result !== null",
            timeout=15000)

    def state(self, page):
        return page.evaluate(
            """() => ({ result: appState.result, answer: appState.lastAnswer,
                        isFractionMode: appState.isFractionMode,
                        lcd: document.getElementById('lcdResultLine').innerText })""")

    def toggle(self, page, mixed=False):
        page.evaluate("(m) => { toggleAnswerFormat(m); }", mixed)
        page.wait_for_timeout(400)
        return self.state(page)


class TestFileModeExactFractions(SToDBase):
    """The reported defect, on the real file:// path."""

    URL = FRONTEND_PATH.as_uri()

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch(channel="chrome")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()

    def test_file_mode_is_actually_in_use(self):
        page = self.make_page(self.URL)
        try:
            self.assertEqual(page.evaluate("() => location.protocol"), "file:")
            self.assertTrue(page.evaluate("() => FILE_MODE"))
        finally:
            page.close()

    def test_repeating_decimal_becomes_the_exact_fraction(self):
        page = self.make_page(self.URL)
        try:
            for expr, exact, _dec in ROUND_TRIP:
                with self.subTest(expr=expr):
                    self.type_expression(page, expr)
                    got = self.toggle(page)
                    self.assertEqual(got["result"], exact)
                    self.assertEqual(got["answer"], exact)
                    self.assertTrue(got["isFractionMode"])
        finally:
            page.close()

    def test_one_third_is_never_the_thousand_denominator_guess(self):
        page = self.make_page(self.URL)
        try:
            self.type_expression(page, "1/3")
            got = self.toggle(page)
            self.assertNotEqual(got["result"], "333/1000")
            self.assertEqual(got["result"], "1/3")
        finally:
            page.close()

    def test_round_trip_restores_the_original_decimal(self):
        # The old bug did not just mislabel the fraction: reading 333/1000
        # back as a number permanently truncated the answer to 0.333.
        page = self.make_page(self.URL)
        try:
            for expr, exact, decimal in ROUND_TRIP:
                with self.subTest(expr=expr):
                    self.type_expression(page, expr)
                    self.toggle(page)
                    back = self.toggle(page)
                    self.assertEqual(back["result"], decimal)
                    self.assertEqual(back["answer"], decimal)
                    self.assertFalse(back["isFractionMode"])
        finally:
            page.close()

    def test_terminating_fraction_is_unchanged(self):
        page = self.make_page(self.URL)
        try:
            self.type_expression(page, "5/8")
            first = self.state(page)
            self.assertEqual(first["result"], "5/8")
            dec = self.toggle(page)
            self.assertEqual(dec["result"], "0.625")
            self.assertEqual(self.toggle(page)["result"], "5/8")
        finally:
            page.close()

    def test_improper_fraction_survives_the_toggle(self):
        page = self.make_page(self.URL)
        try:
            self.type_expression(page, "7/3")
            self.assertEqual(self.toggle(page)["result"], "7/3")
        finally:
            page.close()

    def test_negative_fraction_keeps_its_sign(self):
        page = self.make_page(self.URL)
        try:
            self.type_expression(page, "0-1/3")
            self.assertEqual(self.toggle(page)["result"], "-1/3")
        finally:
            page.close()

    def test_mixed_mode_splits_an_improper_fraction(self):
        page = self.make_page(self.URL)
        try:
            self.type_expression(page, "7/3")
            got = self.toggle(page, mixed=True)
            self.assertEqual(got["result"], "2 1/3")
        finally:
            page.close()

    def test_irrational_is_not_faked_into_a_short_fraction(self):
        page = self.make_page(self.URL)
        try:
            self.type_expression(page, "sqrt(2)")
            got = self.toggle(page)
            # sqrt(2) has no short exact form; the bridge must not invent one.
            self.assertNotIn("/", str(got["result"])[:2])
            self.assertTrue(got["isFractionMode"])
        finally:
            page.close()


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestServedPathAgrees(SToDBase):
    """The served path is the reference: file:// must match it exactly."""

    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, str(FRONTEND_PATH.parent))
        import mvp_server  # noqa: E402

        cls._srv = ThreadingHTTPServer(("127.0.0.1", 0), mvp_server.MvpHandler)
        cls.port = cls._srv.server_address[1]
        threading.Thread(target=cls._srv.serve_forever, daemon=True).start()
        time.sleep(0.4)
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch(channel="chrome")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()
        cls._srv.shutdown()
        cls._srv.server_close()

    def _post(self, path, payload):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def test_server_reference_values(self):
        # Pins what the served path answers for the same numbers.
        self.assertEqual(self._post("/api/fraction", {"value": 1 / 3})["result"], "1/3")
        self.assertEqual(self._post("/api/fraction", {"value": 2 / 3})["result"], "2/3")
        self.assertEqual(self._post("/api/fraction", {"value": 7 / 3})["result"], "7/3")
        self.assertEqual(self._post("/api/fraction", {"value": 5 / 8})["result"], "5/8")

    def test_file_mode_matches_the_served_path(self):
        values = {"1/3": 1 / 3, "2/3": 2 / 3, "7/3": 7 / 3, "1/7": 1 / 7}
        file_page = self.make_page(FRONTEND_PATH.as_uri())
        http_page = self.make_page(f"http://127.0.0.1:{self.port}/")
        try:
            for expr, exact, _dec in ROUND_TRIP:
                with self.subTest(expr=expr):
                    self.type_expression(file_page, expr)
                    file_got = self.toggle(file_page)["result"]
                    served = self._post("/api/fraction", {"value": values[exact]})
                    self.assertEqual(file_got, exact)
                    self.assertEqual(file_got, served["result"])
        finally:
            file_page.close()
            http_page.close()

    def test_served_path_still_renders_the_same_fraction(self):
        page = self.make_page(f"http://127.0.0.1:{self.port}/")
        try:
            self.assertFalse(page.evaluate("() => FILE_MODE"))
            self.type_expression(page, "1/3")
            self.assertEqual(self.toggle(page)["result"], "1/3")
        finally:
            page.close()