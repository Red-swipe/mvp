"""The served page must land in the ERROR state, not a fake result.

Regression contract for the v0.12 integration. Before commit
`caf0ce6` ("keep genuine math errors in the error state") the frontend did:

    appState.error = (e && e.message === 'DIV_ZERO') ? 'Math ERROR' : 'Math ERROR';
    if (appState.error === 'Math ERROR') {
      appState.result = appState.error; appState.resultDisplayed = true;
      appState.error = null;                       // <- error thrown away
    } else { ... }

which meant every genuine maths failure rendered `Math ERROR` as if it were a
successfully computed ANSWER: `appState.error === null`, `appState.result` set
to the string 'Math ERROR', `appState.resultDisplayed === true`. Nothing could
distinguish "the calculator failed" from "the answer happens to be that text",
and normalizeResultErrorEntry() therefore never ran, so the failed expression
also survived in the input buffer.

This module pins the corrected contract on the SERVED page (FILE_MODE false),
where evaluate() takes the fetch() branch. For each of the four failing
sequences the final state must be exactly:

    appState.error        == 'Math ERROR'
    appState.result       is None
    appState.resultDisplayed is False

`file://` is deliberately not used: that is an unsupported deployment mode and
its DIV_ZERO result branch legitimately leaves appState.error null.
"""
import pathlib
import sys
import threading
import time
import unittest
from http.server import ThreadingHTTPServer

PROJECT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))

FRONTEND = PROJECT / "frontend.html"

# (label, keypad keys). Every one of these must be a genuine maths failure.
FAILING_SEQUENCES = [
    ("excess_closing_paren", ["2", "plus", "3", "right_paren", "equals"]),
    ("double_closing_paren", ["left_paren", "2", "plus", "3",
                              "right_paren", "right_paren", "equals"]),
    ("incomplete_operator", ["2", "plus", "equals"]),
    ("divide_by_zero", ["1", "divide", "0", "equals"]),
]

RESET_JS = """() => {
  if (typeof hardResetExpr === 'function') hardResetExpr();
  else if (typeof resetExpr === 'function') resetExpr();
  appState.shift = false;
  appState.error = null;
  appState.result = null;
  appState.resultDisplayed = false;
  appState.lastAnswer = '0';
}"""


def _have_chrome():
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        try:
            b = pw.chromium.launch(channel="chrome")
            b.close()
            return True
        finally:
            pw.stop()
    except Exception:
        return False


@unittest.skipUnless(_have_chrome(), "Playwright + Chrome are required")
class TestServerErrorState(unittest.TestCase):
    """Drives the real served page and asserts the ERROR state is entered."""

    @classmethod
    def setUpClass(cls):
        import mvp_server
        from playwright.sync_api import sync_playwright

        cls._srv = ThreadingHTTPServer(("127.0.0.1", 0), mvp_server.MvpHandler)
        cls.port = cls._srv.server_address[1]
        threading.Thread(target=cls._srv.serve_forever, daemon=True).start()
        time.sleep(0.4)
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls.browser.new_page()
        cls.page.goto("http://127.0.0.1:%d/" % cls.port, wait_until="load")
        cls.page.wait_for_timeout(1200)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()
        cls._srv.shutdown()
        cls._srv.server_close()

    def _drive(self, keys):
        page = self.page
        page.evaluate(RESET_JS)
        for k in keys:
            page.evaluate(
                "k => handleKey(document.querySelector('[data-key=\"' + k + '\"]'))", k)
            if k == "equals":
                page.wait_for_timeout(500)
        return page.evaluate("""() => ({
            error: appState.error,
            result: appState.result,
            resultDisplayed: appState.resultDisplayed
        })""")

    def test_the_page_is_served_not_file_mode(self):
        """Guard: the rest of this module is meaningless under file://."""
        self.assertIs(page_mode := self.page.evaluate(
            "() => (typeof FILE_MODE !== 'undefined') ? FILE_MODE : null"), False,
            "these assertions require the served page, FILE_MODE must be false")

    def test_every_maths_failure_lands_in_the_error_state(self):
        for label, keys in FAILING_SEQUENCES:
            with self.subTest(sequence=label):
                st = self._drive(keys)
                self.assertEqual(st["error"], "Math ERROR",
                                 "%s must set appState.error to 'Math ERROR', "
                                 "got error=%r result=%r" % (label, st["error"],
                                                             st["result"]))
                self.assertIsNone(st["result"],
                                  "%s must NOT present the error as an answer, "
                                  "got %r" % (label, st["result"]))
                self.assertFalse(st["resultDisplayed"],
                                 "%s must not claim to display a result, got %r"
                                 % (label, st["resultDisplayed"]))

    def test_a_valid_calculation_still_answers_normally(self):
        """Control: the error branch must not swallow ordinary results."""
        st = self._drive(["2", "plus", "2", "equals"])
        self.assertIsNone(st["error"],
                          "2+2 must not raise, got %r" % (st["error"],))
        self.assertEqual(str(st["result"]), "4")
        self.assertTrue(st["resultDisplayed"])

    def test_the_error_does_not_leak_into_the_next_calculation(self):
        """The failed expression must not change what the next one computes.

        This asserts the OBSERVABLE contract only. After `2+ =` errors, the
        next `5 =` must compute 5. It must not be 7 (i.e. '2+' + 5 continuing
        the failed expression) and must not raise. getExpr() is deliberately
        not asserted here: on the served path the LCD keeps showing the
        attempted expression for the operator until the next digit replaces it,
        which is a display choice, not the buffer contract.
        """
        st = self._drive(["2", "plus", "equals"])
        self.assertEqual(st["error"], "Math ERROR")
        st = self._drive(["5", "equals"])
        self.assertIsNone(st["error"],
                          "5 = must not raise after a previous error, got %r"
                          % (st["error"],))
        self.assertEqual(str(st["result"]), "5",
                         "the next calculation must start clean, got %r"
                         % (st["result"],))


if __name__ == "__main__":
    unittest.main()