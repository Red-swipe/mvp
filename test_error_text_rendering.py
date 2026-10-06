"""Issue 2 regression: calculator error text must render as plain LCD text.

ROOT CAUSE (confirmed in Chrome by inspecting the live DOM):

`renderLCD()` routed the error string through the same KaTeX path used for
mathematics:

    if (appState.error) renderMath(appState.error, 'lcdResultLine', false);

KaTeX treats `Math ERROR` as MATHEMATICS, not prose: the space is dropped and
every letter becomes its own math-italic `<mi>` glyph. Measured before the fix:

    #lcdResultLine textContent          -> "MathERRORMath ERRORMathERROR"
    descendant tags                    -> SPAN, math, semantics, mrow, mi
    computed font of the letter runs    -> KaTeX_Math   (serif math italic)

So the error was typeset in a serif italic face instead of the ClassWiz LCD
font, and it lost its space. That is the "error font" half of Issue 2.

The fix renders the error as plain text. `.lcd-result-line` is already
`text-align:right` and is covered by `.lcd *`, so the plain string inherits the
LCD face and the right alignment with no extra styling.

Covered:
  ERR-1  each error string renders its exact text, space intact
  ERR-2  no KaTeX wrapper / no `<math>` / no `.katex` around the error
  ERR-3  the error uses the ClassWiz CW Display face, not a KaTeX serif
  ERR-4  the error stays right-aligned
  ERR-5  a real error raised by `=` also renders as plain LCD text
  ERR-6  a successful result is STILL typeset by KaTeX (not regressed)
  ERR-7  clearing the error restores the empty result line
  ERR-8  no console error is introduced
"""
import re
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
FRONTEND_PATH = PROJECT / "frontend.html"
FRONTEND = FRONTEND_PATH.read_text(encoding="utf-8")
URL = FRONTEND_PATH.as_uri()

ERROR_STRINGS = ["Math ERROR", "Syntax ERROR", "Stack ERROR", "Arg ERROR"]
SCREEN_TEXT_FACE = "CWDisplay"

try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:                                          # pragma: no cover
    HAVE_PLAYWRIGHT = False


class TestErrorTextIsNotRoutedThroughKatex(unittest.TestCase):
    """Static guard on the renderLCD decision itself."""

    def test_the_error_branch_does_not_call_render_math(self):
        # Comments are stripped first so the prose that explains this fix
        # cannot satisfy (or trip) the assertion.
        body = strip_comments(FRONTEND)
        start = body.index("function renderLCD(")
        body = body[start:start + 12000]
        m = re.search(r"if\s*\(\s*appState\.error\s*\)\s*\{([^}]*)\}", body, re.S)
        self.assertIsNotNone(m, "the appState.error branch is gone")
        branch = m.group(1)
        self.assertNotIn(
            "renderMath(", branch,
            "appState.error is still routed through renderMath(), which typesets "
            f"the error as serif math italic: {branch[:200]!r}")
        self.assertIn("textContent", branch, branch)


def strip_comments(src):
    out = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    out = re.sub(r"(?m)^\s*//.*$", " ", out)
    return out


def _chrome_available():
    if not HAVE_PLAYWRIGHT:
        return False
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            b.close()
        return True
    except Exception:
        return False


CHROME_OK = _chrome_available()


@unittest.skipUnless(CHROME_OK, "Playwright + Chrome are required")
class ErrorRenderingBrowserCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls._browser.new_page(viewport={"width": 900, "height": 1500})
        cls.console_errors = []
        cls.page.on("console",
                   lambda m: cls.console_errors.append(f"{m.type}: {m.text}")
                   if m.type == "error" else None)
        cls.page.on("pageerror", lambda e: cls.console_errors.append(f"pageerror: {e}"))
        cls.page.goto(URL)
        cls.page.wait_for_timeout(2500)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def setUp(self):
        self.console_errors.clear()
        self.page.evaluate(
            """() => { resetExpr(); appState.shift = false; appState.alpha = false;
                 appState.resultDisplayed = false; appState.result = null;
                 appState.error = null; renderLCD(); }""")

    # -- helpers -------------------------------------------------------
    def show_error(self, message):
        self.page.evaluate("(m) => { appState.error = m; renderLCD(); }", message)
        self.page.wait_for_timeout(150)

    def result_info(self):
        return self.page.evaluate(
            """() => {
                 const el = document.querySelector('#lcdResultLine');
                 const cs = getComputedStyle(el);
                 return {
                   text: el.textContent,
                   hasKatex: !!el.querySelector('.katex'),
                   hasMath: !!el.querySelector('math'),
                   hasMi: !!el.querySelector('mi'),
                   family: cs.fontFamily,
                   align: cs.textAlign,
                   childTags: [...el.querySelectorAll('*')].map(e => e.tagName),
                 };
               }""")


class TestErrorTextRendered(ErrorRenderingBrowserCase):
    """ERR-1 .. ERR-4."""

    def test_each_error_string_renders_exactly_with_its_space(self):
        for message in ERROR_STRINGS:
            with self.subTest(error=message):
                self.show_error(message)
                info = self.result_info()
                self.assertEqual(
                    info["text"], message,
                    f"the error text was altered: {info['text']!r} != {message!r}")

    def test_no_katex_wrapper_math_or_mi_around_the_error(self):
        for message in ERROR_STRINGS:
            with self.subTest(error=message):
                self.show_error(message)
                info = self.result_info()
                self.assertFalse(info["hasKatex"],
                                 f"{message} is still wrapped in a .katex node")
                self.assertFalse(info["hasMath"],
                                 f"{message} still contains a <math> node")
                self.assertFalse(info["hasMi"],
                                 f"{message} still contains math-italic <mi> runs")
                self.assertEqual(
                    info["childTags"], [],
                    f"{message} should be a bare text node, but the result line "
                    f"still holds {info['childTags']}")

    def test_the_error_uses_the_lcd_face_not_a_katex_serif(self):
        for message in ERROR_STRINGS:
            with self.subTest(error=message):
                self.show_error(message)
                family = self.result_info()["family"]
                self.assertIn(SCREEN_TEXT_FACE, family, family)
                self.assertNotIn("KaTeX_", family, family)

    def test_the_error_stays_right_aligned(self):
        for message in ERROR_STRINGS:
            with self.subTest(error=message):
                self.show_error(message)
                self.assertEqual(self.result_info()["align"], "right")


class TestErrorBehaviour(ErrorRenderingBrowserCase):
    """ERR-5 .. ERR-8."""

    def press(self, key, shift=False, alpha=False):
        self.page.evaluate(
            """([k, s, a]) => {
                 const b = document.querySelector('[data-key="' + k + '"]');
                 appState.shift = s; appState.alpha = a;
                 handleKey(b);
                 appState.shift = false; appState.alpha = false;
                 renderLCD();
               }""", [key, shift, alpha])

    def test_a_real_error_from_equals_renders_as_plain_lcd_text(self):
        # `+` then `+` is a malformed expression -> Math ERROR on `=`.
        self.press("1")
        self.press("plus")
        self.press("plus")
        self.press("equals")
        self.page.wait_for_timeout(500)
        self.assertIsNotNone(self.page.evaluate("() => appState.error"),
                             "the malformed expression did not raise an error")
        info = self.result_info()
        self.assertFalse(info["hasKatex"],
                         "a real raised error is still typeset by KaTeX")
        self.assertIn("ERROR", info["text"], info["text"])
        self.assertIn(SCREEN_TEXT_FACE, info["family"], info["family"])

    def test_a_successful_result_is_still_typeset_by_katex(self):
        self.press("2")
        self.press("plus")
        self.press("2")
        self.press("equals")
        self.page.wait_for_timeout(500)
        info = self.result_info()
        self.assertTrue(info["hasKatex"],
                        "the error fix also stopped typesetting real results")
        self.assertIn("4", info["text"], info["text"])

    def test_clearing_the_error_restores_an_empty_result_line(self):
        self.show_error("Math ERROR")
        self.page.evaluate(
            """() => { appState.error = null; appState.result = null;
                 appState.resultDisplayed = false; renderLCD(); }""")
        self.page.wait_for_timeout(150)
        self.assertEqual(self.result_info()["text"].strip(), "")

    def test_no_console_error_is_introduced(self):
        for message in ERROR_STRINGS:
            self.show_error(message)
        self.assertEqual(self.console_errors, [],
                         f"console errors: {self.console_errors}")


if __name__ == "__main__":
    unittest.main()