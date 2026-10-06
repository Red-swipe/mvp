"""Issue 1 regression: the LCD digits must all be the ClassWiz CW Display face.

ROOT CAUSE (confirmed in a real browser, not by reading the stylesheet):
the screen-text rule `.lcd, .lcd *:not(.katex):not(.katex *)` deliberately
stops at `.katex`, so it never reached the digits. But BOTH the expression
line and the result line are typeset by KaTeX, so every digit on screen was
painted in `KaTeX_Main` / `KaTeX_AMS` -- a Times-style serif -- while the
surrounding plain LCD text used CW Display. Two unrelated numeral designs
on one screen is what made the digits read as "tacky".

Measured before the fix (Chrome, `getComputedStyle`):
    expression digit run -> font-family: KaTeX_AMS
    result      digit run -> font-family: KaTeX_Main, "Times New Roman", serif
    both                   -> font-variant-numeric: normal

The fix marks digit-only leaf `.mord` runs with `.lcd-digit-run` after each
KaTeX render and re-faces only those. Structural `.mord`s that carry a
vlist (fractions, radicals, big operators) are never marked, so KaTeX's
own em-based metrics for those constructs are untouched.

Covered:
  DIG-1  every digit run on the expression line uses the LCD stack
  DIG-2  every digit run on the result line uses the LCD stack
  DIG-3  both carry `font-variant-numeric: lining-nums tabular-nums`
  DIG-4  no digit run resolves to any `KaTeX_*` face
  DIG-5  the 1234567890 case renders and is visible in both lines
  DIG-6  the LCD stack is identical in the input and the result line
  DIG-7  digit ink height agrees between input and result (same cap ratio)
  DIG-8  fraction / radical / big-operator wrappers are NOT re-faced
  DIG-9  the `.lcd-digit-run` rule cannot escape the LCD wrapper
  DIG-10 no `monospace`-only override on the LCD expression/result elements
  DIG-11 no browser console error is introduced
"""
import re
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
FRONTEND_PATH = PROJECT / "frontend.html"
FRONTEND = FRONTEND_PATH.read_text(encoding="utf-8")
URL = FRONTEND_PATH.as_uri()

# The genuine ClassWiz CW Display face (SIL OFL 1.1) that the screen must use.
SCREEN_TEXT_FACE = "CWDisplay"
DIGIT_RUN_CLASS = "lcd-digit-run"
EXPECTED_DIGITS = "1234567890"

try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:                                          # pragma: no cover
    HAVE_PLAYWRIGHT = False


def strip_comments(src):
    out = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    out = re.sub(r"(?m)^\s*//.*$", " ", out)
    return out


CSS_NO_COMMENTS = strip_comments(FRONTEND)


# --------------------------------------------------------------------------
# Static: the rule that re-faces digits
# --------------------------------------------------------------------------
class TestDigitRunRule(unittest.TestCase):
    """DIG-9 / DIG-10."""

    def _digit_rule(self):
        m = re.search(
            r"([^{}]*\.lcd-digit-run[^{}]*)\{([^}]*)\}", CSS_NO_COMMENTS)
        self.assertIsNotNone(m, f"no CSS rule targets .{DIGIT_RUN_CLASS}")
        return m.group(1), m.group(2)

    def test_the_digit_rule_is_scoped_to_the_lcd_wrapper(self):
        selectors, body = self._digit_rule()
        self.assertIn(".katex-lcd-wrap", selectors, selectors)
        self.assertIn("#lcdDisplay", selectors, selectors)

    def test_the_digit_rule_uses_the_lcd_stack_and_numeric_variants(self):
        selectors, body = self._digit_rule()
        self.assertIn("var(--lcd-font)", body, body)
        variant = re.search(r"font-variant-numeric\s*:\s*([^;]+);", body)
        self.assertIsNotNone(variant, "the digit rule sets no font-variant-numeric")
        self.assertIn("lining-nums", variant.group(1), variant.group(1))
        self.assertIn("tabular-nums", variant.group(1), variant.group(1))

    def test_the_digit_rule_names_no_katex_face(self):
        selectors, body = self._digit_rule()
        self.assertNotIn("KaTeX_", body, body)

    def test_no_monospace_only_override_on_the_lcd_elements(self):
        # A previously fixed bug was a bare `font-family: monospace` on these
        # elements, which bypassed the CW Display face entirely. It must not
        # come back on the expression or the result line.
        for selector in (".lcd-expr-content", ".lcd-result-line"):
            for m in re.finditer(re.escape(selector) + r"\s*(?:,[^{]*)?\{([^}]*)\}",
                                 CSS_NO_COMMENTS):
                body = m.group(1)
                fm = re.search(r"font-family\s*:\s*([^;]+);", body)
                if fm:
                    self.assertNotEqual(
                        fm.group(1).strip().strip('"\''), "monospace",
                        f"{selector} sets font-family: monospace again, which "
                        "bypasses the ClassWiz LCD face: " + fm.group(1))


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
class LcdDigitsBrowserCase(unittest.TestCase):
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
    def types(self, text):
        for ch in text:
            self.page.evaluate("(c) => { insertToken(c); }", ch)

    def evaluate_result(self):
        self.page.evaluate("() => { doCalc(); }")
        self.page.wait_for_timeout(400)

    def runs_in(self, host):
        """Computed style of every marked digit run inside `host`."""
        return self.page.evaluate(
            """([h, cls]) => [...document.querySelectorAll(h + ' .' + cls)]
                 .map(e => { const cs = getComputedStyle(e);
                             return { text: e.textContent, family: cs.fontFamily,
                                      variant: cs.fontVariantNumeric,
                                      size: parseFloat(cs.fontSize) }; })""",
            [host, DIGIT_RUN_CLASS])


class TestDigitsRendered(LcdDigitsBrowserCase):
    """DIG-1 .. DIG-7 / DIG-11."""

    def test_1234567890_input_and_result_use_the_lcd_stack(self):
        self.types(EXPECTED_DIGITS)
        self.page.wait_for_timeout(250)
        self.evaluate_result()

        for host, label in (("#lcdExprContent", "expression"),
                            ("#lcdResultLine", "result")):
            runs = self.runs_in(host)
            self.assertTrue(runs, f"no digit runs marked on the {label} line")
            digits = [r for r in runs if EXPECTED_DIGITS in r["text"]]
            self.assertTrue(
                digits, f"{label} line has no digit run holding {EXPECTED_DIGITS}: "
                        f"{runs}")
            for run in digits:
                self.assertIn(
                    SCREEN_TEXT_FACE, run["family"],
                    f"the {label} line still paints {EXPECTED_DIGITS} with "
                    f"{run['family']!r}, not the CW Display face")
                self.assertNotIn(
                    "KaTeX_", run["family"],
                    f"the {label} line still resolves digits to a KaTeX face: "
                    f"{run['family']!r}")

    def test_no_digit_run_anywhere_on_the_lcd_uses_a_katex_face(self):
        self.types(EXPECTED_DIGITS)
        self.evaluate_result()
        runs = self.runs_in("#lcdDisplay")
        self.assertTrue(runs, "no digit runs found anywhere on the LCD")
        bad = [r for r in runs if "KaTeX_" in r["family"]]
        self.assertEqual(
            bad, [],
            f"these digit runs still resolve to a KaTeX face: {bad}")

    def test_digit_runs_carry_lining_and_tabular_numerics(self):
        self.types(EXPECTED_DIGITS)
        self.evaluate_result()
        for host in ("#lcdExprContent", "#lcdResultLine"):
            runs = self.runs_in(host)
            self.assertTrue(runs, f"no digit runs on {host}")
            for run in runs:
                self.assertIn(
                    "lining-nums", run["variant"],
                    f"{host} digit run has font-variant-numeric "
                    f"{run['variant']!r}, expected lining-nums")
                self.assertIn(
                    "tabular-nums", run["variant"],
                    f"{host} digit run has font-variant-numeric "
                    f"{run['variant']!r}, expected tabular-nums")

    def test_the_plain_lcd_elements_still_carry_the_numeric_variants(self):
        """The pre-existing `.lcd` rule must not have been lost."""
        info = self.page.evaluate(
            """() => { const cs = getComputedStyle(document.querySelector('.lcd'));
                       return { family: cs.fontFamily, variant: cs.fontVariantNumeric }; }""")
        self.assertIn(SCREEN_TEXT_FACE, info["family"], info["family"])
        self.assertIn("lining-nums", info["variant"], info["variant"])
        self.assertIn("tabular-nums", info["variant"], info["variant"])

    def test_input_and_result_use_one_identical_font_stack(self):
        self.types(EXPECTED_DIGITS)
        self.evaluate_result()
        expr = [r for r in self.runs_in("#lcdExprContent") if EXPECTED_DIGITS in r["text"]]
        res = [r for r in self.runs_in("#lcdResultLine") if EXPECTED_DIGITS in r["text"]]
        self.assertTrue(expr and res)
        self.assertEqual(
            expr[0]["family"], res[0]["family"],
            "the input and the result line still disagree on the font stack: "
            f"{expr[0]['family']!r} vs {res[0]['family']!r}")

    def test_digits_share_one_metric_basis_between_input_and_result(self):
        """Same face + `tabular-nums` => one advance width per em, so the
        digits sit on one baseline pitch and one visual height on both lines.

        Measured with a canvas rather than a DOM rect: the DOM box also carries
        KaTeX's own strut, whose height comes from KaTeX's faces and is not the
        digit glyph height. The canvas asks the resolved font directly.

        The canvas is measured at ONE reference size for both lines: the input
        and the result use different font sizes by design, and `0.875em` of ink
        rasterises to a slightly different fraction of 16px than of 20px, which
        would otherwise read as a glyph mismatch when the outlines are in fact
        identical.
        """
        self.types(EXPECTED_DIGITS)
        self.evaluate_result()
        metrics = self.page.evaluate(
            """([cls]) => {
                 const REF = 100;                    // px, big enough to avoid
                 const measure = (host) => {         // rasterisation rounding
                   const el = [...document.querySelectorAll(host + ' .' + cls)]
                     .find(e => e.textContent.trim() === DIGITS);
                   if (!el) return null;
                   const cs = getComputedStyle(el);
                   const ctx = document.createElement('canvas').getContext('2d');
                   ctx.font = REF + 'px ' + cs.fontFamily;
                   const m0 = ctx.measureText('0');
                   const m8 = ctx.measureText('8');
                   return { fontSize: parseFloat(cs.fontSize),
                            advancePerEm: +(m0.width / REF).toFixed(4),
                            inkPerEm: +((m0.actualBoundingBoxAscent +
                                         m0.actualBoundingBoxDescent) / REF).toFixed(4),
                            monospacedDigits: Math.abs(m0.width - m8.width) < 0.01 };
                 };
                 return { expr: measure('#lcdExprContent'),
                          result: measure('#lcdResultLine') };
               }""".replace("DIGITS", repr(EXPECTED_DIGITS)),
            [DIGIT_RUN_CLASS])
        self.assertIsNotNone(metrics["expr"], "no expression digit run measured")
        self.assertIsNotNone(metrics["result"], "no result digit run measured")
        for label, m in metrics.items():
            self.assertTrue(
                m["monospacedDigits"],
                f"the {label} line digits are not fixed-pitch (tabular-nums is "
                f"not in effect): {m}")
        self.assertAlmostEqual(
            metrics["expr"]["advancePerEm"], metrics["result"]["advancePerEm"],
            places=3,
            msg=f"digit pitch per em differs between input and result: {metrics}")
        self.assertAlmostEqual(
            metrics["expr"]["inkPerEm"], metrics["result"]["inkPerEm"], places=3,
            msg=f"digit height per em differs between input and result: {metrics}")

    def test_1234567890_is_visible_in_both_lines(self):
        self.types(EXPECTED_DIGITS)
        self.page.wait_for_timeout(200)
        self.evaluate_result()
        self.assertIn(EXPECTED_DIGITS, self.page.inner_text("#lcdExprContent"))
        self.assertIn(EXPECTED_DIGITS, self.page.inner_text("#lcdResultLine"))

    def test_no_console_error_is_introduced(self):
        self.types(EXPECTED_DIGITS)
        self.evaluate_result()
        self.page.wait_for_timeout(200)
        self.assertEqual(self.console_errors, [],
                         f"console errors: {self.console_errors}")


class TestKaTeXStructuresUntouched(LcdDigitsBrowserCase):
    """DIG-8: a vlist wrapper must never be re-faced."""

    def test_a_fraction_wrapper_is_not_marked(self):
        self.page.evaluate(
            """() => { resetExpr(); renderLCD();
                 insertToken('1'); insertToken('2');
                 handleKey(document.querySelector('[data-key="fraction"]'));
                 insertToken('3'); insertToken('4'); renderLCD(); }""")
        self.page.wait_for_timeout(400)
        self.assertTrue(self.page.query_selector("#lcdExprContent .mfrac"),
                        "the fraction was not typeset, so nothing was proved")
        marked = self.page.evaluate(
            """(cls) => [...document.querySelectorAll('#lcdExprContent')]
                 .filter(e => e.classList.contains('mfrac') && e.classList.contains(cls))
                 .map(e => e.className)""",
            DIGIT_RUN_CLASS)
        self.assertEqual(
            marked, [],
            "a .mfrac wrapper was re-faced; that desyncs the fraction bar from "
            f"its contents: {marked}")

    def test_the_numerator_and_denominator_digits_are_still_re_faced(self):
        self.page.evaluate(
            """() => { resetExpr(); renderLCD();
                 insertToken('1'); insertToken('2');
                 handleKey(document.querySelector('[data-key="fraction"]'));
                 insertToken('3'); insertToken('4'); renderLCD(); }""")
        self.page.wait_for_timeout(400)
        runs = self.runs_in("#lcdExprContent")
        texts = {r["text"] for r in runs}
        self.assertTrue(
            texts & {"12", "34"},
            f"the fraction's digits were not re-faced: {sorted(texts)}")
        for run in runs:
            if run["text"] in {"12", "34"}:
                self.assertIn(SCREEN_TEXT_FACE, run["family"], run["family"])


if __name__ == "__main__":
    unittest.main()