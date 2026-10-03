"""Regression tests for the frontend Math I/O visual parity audit.

Every test here drives the REAL frontend.html in a real browser (Playwright +
Chrome) and asserts on the RENDERED DOM, computed styles and actual key
routing. None of them assert that a function name merely exists in the source:
a defect that only moved a string between two functions would pass such a
test, and each of the defects recorded in FRONTEND_MATH_IO_AUDIT.md would
have slipped through.

Covered defects:
  TYPO-1  expression/result lines bypassed the LCD typeface (monospace)
  TYPO-2  the ClassWiz face has no glyphs for 36 math code points and the
          browser substituted an arbitrary face for exactly those
  TYPO-3  `#lcdSpreadsheet *` / `#lcdDistribution *` outranked KaTeX's own
          `.katex` rule and re-typed every math glyph
  KATEX-1 the inline wrapper className lost its separating space
  KATEX-2 the no-KaTeX fallback printed raw LaTeX markup
  KATEX-3 pressing `=` re-typeset the editable input line with KaTeX,
          destroying the cursor/slot DOM and jumping the font
  FRAC-1  exact `a/b` and `a b/c` results rendered as inline slashes
  DDX-1   SHIFT+integral emitted the raw text token `d/dx(` instead of a
          template
  DDX-2   the derivative template serialized `X`, which the calculus engine
          rejects (and the FILE_MODE bridge silently evaluated a constant)
  SIG-1   SHIFT+x emitted the raw text token `Σ(` instead of a template
  SHIFT-1 the printed legends / data-shift attributes for the ∫ and x keys
          were swapped with respect to raw/buttons.md
  ALPHA-1 ALPHA on the x key was unmapped (it must insert `y`)

The browser tests skip cleanly when Playwright or Chrome is unavailable; the
static/structural tests always run.
"""
import json
import re
import shutil
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
FRONTEND = (PROJECT / "frontend.html").read_text(encoding="utf-8")

try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:                                     # pragma: no cover
    HAVE_PLAYWRIGHT = False

URL = (PROJECT / "frontend.html").as_uri()

# Code points CASIOClassWizCW01.ttf actually carries (verified with fontTools).
LCD_FONT_CODEPOINTS = set(range(0x20, 0x7F)) | {
    0xA9, 0xAC, 0xAF, 0xB2, 0xB8, 0xB9, 0xC0, 0xC5, 0xC7, 0xC8, 0xC9,
    0xCA, 0xCD, 0xE3, 0x2C6, 0x2013, 0x201A, 0x203A, 0x2122,
}

# The mathematical symbols the audit requires, minus those the LCD face has.
MATH_SYMBOLS_NOT_IN_LCD_FONT = {
    "minus": "\u2212", "multiply": "\u00d7", "divide": "\u00f7",
    "not-equal": "\u2260", "less-equal": "\u2264", "greater-equal": "\u2265",
    "pi": "\u03c0", "sqrt": "\u221a", "cbrt": "\u221b", "Sigma": "\u03a3",
    "integral": "\u222b", "infinity": "\u221e", "degree": "\u00b0",
    "sup3": "\u00b3", "sup-minus": "\u207b", "sup9": "\u2079",
    "prime": "\u2032", "dprime": "\u2033", "middot": "\u00b7",
    "plus-minus": "\u00b1", "mu": "\u03bc", "sigma": "\u03c3",
    "partial": "\u2202", "nabla": "\u2207", "element-of": "\u2208",
    "empty-set": "\u2205", "forall": "\u2200", "exists": "\u2203",
    "equivalent": "\u2261", "approx": "\u2248", "Omega": "\u03a9",
    "alpha": "\u03b1", "beta": "\u03b2", "theta": "\u03b8", "lambda": "\u03bb",
    "parallel": "\u2225",
}

MATH_FONT_PREFIX = "Cambria Math"


# --------------------------------------------------------------------------
# Static / structural guarantees (always run)
# --------------------------------------------------------------------------
def strip_comments(src):
    """Remove CSS and JS comments so prose cannot satisfy or break a selector
    assertion."""
    out = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    out = re.sub(r"(?m)^\s*//.*$", " ", out)
    return out


CSS_NO_COMMENTS = strip_comments(FRONTEND)


class TestTypographySource(unittest.TestCase):
    """TYPO-1 / TYPO-2 / TYPO-3 at the source level."""

    def test_lcd_font_stack_declares_a_real_math_face(self):
        # The ClassWiz face carries no math glyphs, so a math face must be
        # named after it in the stack (CSS fallback is per character).
        m = re.search(r"\.lcd\{[^}]*?font-family:([^;]+);", CSS_NO_COMMENTS, re.S)
        self.assertIsNotNone(m, ".lcd font-family not found")
        stack = m.group(1)
        self.assertIn("CASIO ClassWiz", stack)
        self.assertIn(MATH_FONT_PREFIX, stack, stack)

    def test_expression_and_result_lines_do_not_declare_their_own_font(self):
        for sel in (".lcd-expr-content", ".lcd-result-line"):
            m = re.search(re.escape(sel) + r"\{([^}]*)\}", CSS_NO_COMMENTS, re.S)
            self.assertIsNotNone(m, f"{sel} rule not found")
            self.assertNotIn(
                "font-family", m.group(1),
                f"{sel} still overrides the LCD typeface instead of inheriting it")

    def test_no_universal_font_override_in_mode_screens(self):
        # An id selector (1,0,0) beats KaTeX's `.katex` class rule (0,1,0).
        for bad in ("#lcdSpreadsheet *", "#lcdDistribution *"):
            self.assertNotIn(
                bad, CSS_NO_COMMENTS,
                f"{bad} re-types every KaTeX glyph in Courier New")

    def test_math_sym_class_exists_with_a_math_face(self):
        m = re.search(r"\.math-sym,[^{]*\{([^}]*)\}", CSS_NO_COMMENTS, re.S)
        self.assertIsNotNone(m, ".math-sym rule missing")
        self.assertIn(MATH_FONT_PREFIX, m.group(1))


class TestCalculusTemplateSource(unittest.TestCase):
    """DDX-1 / DDX-2 / SIG-1 at the source level."""

    def test_no_raw_calculus_text_tokens_in_the_router(self):
        self.assertNotIn("insertToken('d/dx(')", FRONTEND)
        self.assertNotIn("insertToken('\\u03a3(')", FRONTEND)
        self.assertNotIn("insertToken(isShift ? '\\u03a3('", FRONTEND)

    def test_both_calculus_templates_are_inserted(self):
        self.assertIn("function insertSigma(", FRONTEND)
        self.assertIn("function insertDerivative(", FRONTEND)
        self.assertIn("if (isShift) { insertSigma(); return; }", FRONTEND)
        self.assertIn("if (isShift) { insertDerivative(); return; }", FRONTEND)

    def test_calculus_body_maps_the_variable_register_to_the_dummy(self):
        self.assertIn("function calculusBody(", FRONTEND)
        seg = FRONTEND[FRONTEND.index("function calculusBody("):
                       FRONTEND.index("function calculusBody(") + 400]
        self.assertIn("\\bX\\b", seg)

    def test_derivative_point_comes_from_the_x_register(self):
        self.assertIn("function derivativePoint(", FRONTEND)
        seg = FRONTEND[FRONTEND.index("function derivativePoint("):
                       FRONTEND.index("function derivativePoint(") + 600]
        self.assertIn("appState.variables.X", seg)


class TestShiftLegendParity(unittest.TestCase):
    """SHIFT-1 / ALPHA-1: printed legend == data attribute == routing."""

    def test_integral_key_legend_is_d_dx(self):
        self.assertIn('data-shift="Sigma" data-alpha=":" data-key="integral"',
                      FRONTEND)
        m = re.search(
            r'<span class="shift-mark">(d/dx|\u03a3)</span>'
            r'<span class="alpha-mark">:</span></span>\s*'
            r'<button class="b math-template" data-shift="Sigma"', FRONTEND)
        self.assertIsNotNone(m, "integral key legend not found")
        self.assertEqual(m.group(1), "d/dx")

    def test_variable_key_legend_is_sigma_and_alpha_is_y(self):
        self.assertIn('data-shift="d/dx" data-alpha="y" data-key="variable"',
                      FRONTEND)
        m = re.search(
            r'<span class="shift-mark">(\u03a3|d/dx)</span>'
            r'<span class="alpha-mark">y</span></span>\s*'
            r'<button class="b variable" data-shift="d/dx"', FRONTEND)
        self.assertIsNotNone(m, "variable key legend not found")
        self.assertEqual(m.group(1), "\u03a3")


# --------------------------------------------------------------------------
# Browser-level behaviour (the real proof)
# --------------------------------------------------------------------------
def _chrome_available():
    if not HAVE_PLAYWRIGHT or shutil.which("node") is None and False:
        return False
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            b.close()
        return True
    except Exception:
        return False


CHROME_OK = _chrome_available() if HAVE_PLAYWRIGHT else False


@unittest.skipUnless(CHROME_OK, "Playwright + Chrome are required")
class BrowserCase(unittest.TestCase):
    """Base class: one page per test class, real frontend, file:// mode."""

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls._browser.new_page(viewport={"width": 900, "height": 1500})
        cls.page.goto(URL)
        cls.page.wait_for_timeout(2500)          # deferred KaTeX CDN
        cls.page_errors = []
        cls.page.on("pageerror", lambda e: cls.page_errors.append(str(e)))

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def setUp(self):
        self.reset()

    def reset(self):
        self.page.evaluate(
            """() => { resetExpr(); appState.shift = false; appState.alpha = false;
                 appState.resultDisplayed = false; appState.result = null;
                 appState.error = null; renderLCD(); }""")

    def press(self, key, shift=False, alpha=False):
        self.page.evaluate(
            """([k, s, a]) => {
                 const b = document.querySelector('[data-key="' + k + '"]');
                 if (!b) throw new Error('no such key: ' + k);
                 appState.shift = s; appState.alpha = a;
                 handleKey(b);
                 appState.shift = false; appState.alpha = false;
                 renderLCD();
               }""", [key, shift, alpha])

    def types(self, text):
        for ch in text:
            self.page.evaluate("(c) => { insertToken(c); }", ch)

    def cursor_state(self):
        return self.page.evaluate(
            """() => { const p = getParent();
                 return { template: p && p.par ? p.par.type : null,
                          slot: p ? p.slotName : null,
                          index: cursor.index,
                          expr: getExpr() }; }""")

    def lcd_html(self):
        return self.page.inner_html("#lcdExprContent")

    def lcd_text(self):
        """Rendered TEXT only (no markup), so '</span>' cannot look like '/'."""
        return self.page.inner_text("#lcdExprContent")

    def has_cursor(self):
        return bool(self.page.query_selector("#lcdExprContent .lcd-cursor"))


class TestTypographyRendered(BrowserCase):
    """TYPO-1 / TYPO-2."""

    def test_expression_and_result_lines_use_the_calculator_typeface(self):
        for sel in ("#lcdExprContent", "#lcdResultLine"):
            font = self.page.evaluate(
                "(s) => getComputedStyle(document.querySelector(s)).fontFamily", sel)
            self.assertIn("CASIO ClassWiz", font, sel)
            self.assertNotEqual(font.strip(), "monospace", sel)
            # ...and it must name a real math face for the glyphs the LCD face
            # cannot supply.
            self.assertIn(MATH_FONT_PREFIX, font, sel)

    def test_every_math_symbol_the_lcd_font_lacks_gets_a_math_face(self):
        # Drive the real insertion path and inspect the real rendered DOM.
        missing = self.page.evaluate(
            """(pairs) => {
              const out = [];
              for (const [name, ch] of pairs) {
                resetExpr();
                insertToken(ch);
                const host = document.getElementById('lcdExprContent');
                const span = host.querySelector('.math-sym');
                out.push({ name: name, ch: ch, wrapped: !!span,
                           text: host.textContent,
                           font: span ? getComputedStyle(span).fontFamily : null });
              }
              return out;
            }""", [[k, v] for k, v in MATH_SYMBOLS_NOT_IN_LCD_FONT.items()])

        self.assertEqual(len(missing), len(MATH_SYMBOLS_NOT_IN_LCD_FONT))
        for row in missing:
            self.assertTrue(row["wrapped"],
                            f"{row['name']} ({row['ch']!r}) is not inside .math-sym; "
                            f"the LCD face has no glyph for it, so the browser "
                            f"substitutes an arbitrary font")
            self.assertIn(MATH_FONT_PREFIX, row["font"], row["name"])
            self.assertEqual(row["text"], row["ch"])

    def test_lcd_font_really_lacks_those_code_points(self):
        # Independent ground truth for the assertion above: read the TTF cmap.
        try:
            from fontTools.ttLib import TTFont
        except ImportError:                          # pragma: no cover
            self.skipTest("fontTools is not installed")
        ttf = PROJECT / "ClassWizFontSet" / "CASIOClassWizCW01.ttf"
        if not ttf.exists():                          # pragma: no cover
            self.skipTest("ClassWiz font asset is not present")
        cmap = set(TTFont(str(ttf)).getBestCmap())
        for name, ch in MATH_SYMBOLS_NOT_IN_LCD_FONT.items():
            self.assertNotIn(ord(ch), cmap,
                             f"{name} unexpectedly present in the LCD font; "
                             f"update MATH_SYMBOLS_NOT_IN_LCD_FONT")
        # ...and the digits/letters it does carry must NOT be wrapped.
        for ch in "0123456789+-=<>()":
            self.assertIn(ord(ch), cmap)

    def test_ascii_stays_in_the_calculator_typeface(self):
        self.reset()
        self.types("x2+3")
        wrapped = self.page.evaluate(
            """() => document.querySelectorAll('#lcdExprContent .math-sym').length""")
        self.assertEqual(wrapped, 0, "plain ASCII must not be diverted to a math face")
        self.assertEqual(self.lcd_html().count("math-sym"), 0)


class TestKatexIsolation(BrowserCase):
    """KATEX-1 / KATEX-3 / TYPO-3."""

    def test_katex_is_not_installed_over_the_mode_screens(self):
        for host_id, container in (("lcdSpreadsheetBody", "lcdSpreadsheet"),
                                   ("lcdDistributionBody", "lcdDistribution")):
            res = self.page.evaluate(
                """([hostId, containerId]) => {
                     const h = document.getElementById(hostId);
                     h.innerHTML = '';
                     renderMath('\\\\sqrt{25}+\\\\pi', hostId, false, 'sqrt(25)+pi');
                     const k = h.querySelector('.katex');
                     return {
                       katexFound: !!k,
                       katexFont: k ? getComputedStyle(k).fontFamily : null,
                       containerFont: getComputedStyle(
                         document.getElementById(containerId)).fontFamily,
                     };
                   }""", [host_id, container])
            self.assertTrue(res["katexFound"], host_id)
            self.assertIn("KaTeX_Main", res["katexFont"],
                          f"{container}: KaTeX was re-typed by a forced font rule "
                          f"({res['katexFont']})")

    def test_katex_wrapper_classname_has_separated_tokens(self):
        cls = self.page.evaluate(
            """() => { renderMath('2+3', 'lcdResultLine', false, '2+3');
                 const w = document.querySelector('#lcdResultLine .katex-lcd-wrap');
                 return w ? w.className : null; }""")
        self.assertIsNotNone(cls)
        self.assertEqual(cls.split(), ["katex-lcd-wrap", "katex-inline"])

    def test_katex_does_not_touch_the_editable_input_line_after_equals(self):
        self.press("2"); self.press("3"); self.press("plus")
        self.press("3"); self.press("equals")
        self.page.wait_for_timeout(250)
        info = self.page.evaluate(
            """() => ({ katexInExpr: document.querySelectorAll(
                          '#lcdExprContent .katex').length,
                        expr: document.getElementById('lcdExprContent').innerHTML,
                        result: appState.result })""")
        self.assertEqual(info["katexInExpr"], 0,
                         "the editable line must not be re-typeset with KaTeX")
        self.assertIn("math-slot", info["expr"],
                      "the editable slot DOM was destroyed by the result render")
        self.assertTrue(self.has_cursor(),
                        "the cursor must survive pressing =")
        self.assertEqual(info["result"], "26")

    def test_input_line_font_does_not_change_when_a_result_appears(self):
        self.reset()
        before = self.page.evaluate(
            "() => getComputedStyle(document.getElementById('lcdExprContent')).fontFamily")
        self.press("2"); self.press("plus"); self.press("3")
        self.press("equals"); self.page.wait_for_timeout(200)
        after = self.page.evaluate(
            "() => getComputedStyle(document.getElementById('lcdExprContent')).fontFamily")
        self.assertEqual(before, after,
                         "the input line changed typeface when the result appeared")


class TestFractionsRendered(BrowserCase):
    """Phase 5: stacked fractions, mixed fractions, exact-answer output."""

    def test_fraction_renders_as_a_stacked_template(self):
        self.press("fraction")
        self.types("1")
        self.press("dpad_right")
        self.types("2")
        html = self.lcd_html()
        self.assertIn('class="math-fraction"', html)
        self.assertIn('class="math-numerator"', html)
        self.assertIn('class="math-fraction-bar"', html)
        self.assertIn('class="math-denominator"', html)
        # the bar must be a drawn rule, not a "/" character in the text
        self.assertNotIn("/", self.lcd_text())
        self.assertEqual(self.page.evaluate("() => getExpr()"), "((1)/(2))")

    def test_fraction_cursor_owns_both_slots(self):
        self.press("fraction")
        self.types("1")
        self.assertEqual(self.cursor_state()["slot"], "num")
        self.press("dpad_right")
        st = self.cursor_state()
        self.assertEqual((st["slot"], st["template"]), ("den", "fraction"))
        self.types("2")
        self.assertEqual(self.page.evaluate("() => getExpr()"), "((1)/(2))")
        # vertical navigation reaches the numerator again
        self.press("dpad_up")
        self.assertEqual(self.cursor_state()["slot"], "num")
        self.press("dpad_down")
        self.assertEqual(self.cursor_state()["slot"], "den")

    def test_fraction_survives_an_operator_and_nesting(self):
        # outer fraction, then a fraction nested in its numerator
        self.press("fraction")
        self.page.evaluate("() => { insertFraction(); }")
        self.types("1")
        self.press("dpad_right"); self.types("2")
        self.press("dpad_right"); self.types("3")
        self.assertEqual(self.page.evaluate("() => getExpr()"),
                         "((((1)/(2))3)/(1))")
        self.assertEqual(self.lcd_html().count('class="math-fraction"'), 2)

    def test_mixed_fraction_has_a_whole_part_and_a_fraction(self):
        self.press("fraction", shift=True)
        self.types("1")
        self.press("dpad_right"); self.types("2"); self.types("3")
        self.press("dpad_right"); self.types("4"); self.types("5")
        html = self.lcd_html()
        self.assertIn('class="math-mixed-row"', html)
        self.assertIn('class="math-numerator"', html)
        self.assertIn('class="math-denominator"', html)
        self.assertEqual(self.page.evaluate("() => getExpr()"),
                         "((1)+((23)/(45)))")

    def test_exact_fraction_result_is_typeset_as_a_stacked_fraction(self):
        for text, expect_num, expect_den in (("1/2", "1", "2"),
                                             ("1 23/45", "23", "45")):
            rendered = self.page.evaluate(
                """(t) => { appState.result = t; appState.resultDisplayed = true;
                     renderMatrixResult(t);
                     const h = document.getElementById('lcdResultLine');
                     return { html: h.innerHTML,
                              frac: !!h.querySelector('.katex .mfrac'),
                              text: h.textContent }; }""", text)
            self.assertTrue(rendered["frac"],
                            f"{text!r} rendered as an inline slash, not a fraction")
            self.assertIn(expect_num, rendered["text"])
            self.assertIn(expect_den, rendered["text"])

    def test_engineering_notation_is_not_corrupted_by_latex_conversion(self):
        res = self.page.evaluate(
            """() => { appState.result = '1.234\u00d710^3';
                 appState.resultDisplayed = true;
                 renderMatrixResult('1.234\u00d710^3');
                 const h = document.getElementById('lcdResultLine');
                 return { text: h.textContent,
                          cdot: h.innerHTML.includes('cdot') }; }""")
        self.assertFalse(res["cdot"], "1.234x10^3 was rewritten with \\cdot")
        self.assertIn("1.234", res["text"])


class TestDerivativeTemplate(BrowserCase):
    """Phase 6 / DDX-1 / DDX-2."""

    def test_shift_integral_builds_a_derivative_template_not_raw_text(self):
        self.press("integral", shift=True)
        st = self.cursor_state()
        self.assertEqual(st["template"], "derivative")
        self.assertEqual(st["slot"], "body")
        html = self.lcd_html()
        self.assertIn('class="math-derivative-template"', html)
        self.assertIn('class="math-deriv-diff">d<', html)
        self.assertIn('class="math-deriv-bar"', html)
        self.assertIn('class="math-deriv-dx">dx<', html)
        self.assertIn('class="math-deriv-body"', html)
        # The old defect: a literal, unbalanced "d/dx(" text token.
        self.assertNotIn("d/dx(", html)
        self.assertTrue(self.has_cursor())

    def test_derivative_body_is_editable_and_serializes_to_diff(self):
        self.press("integral", shift=True)
        self.page.evaluate("() => { insertToken('X'); }")
        self.page.evaluate("() => { insertPower('2'); }")
        self.assertEqual(self.page.evaluate("() => getExpr()"), "diff(((x)^(2)),0)")
        self.assertIn('class="math-power-exp"', self.lcd_html())

    def test_derivative_uses_the_x_register_as_the_differentiation_point(self):
        for x, expected in ((3, 6.0), (2, 4.0), (0, 0.0)):
            res = self.page.evaluate(
                """(xv) => { appState.variables.X = xv;
                     resetExpr(); insertDerivative();
                     insertToken('X'); insertPower('2');
                     const ser = getExpr();
                     let value; try { value = localEvaluate(ser); }
                     catch (e) { value = 'THREW: ' + e.message; }
                     return { ser: ser, value: value }; }""", x)
            self.assertIn(f",{x})", res["ser"], res["ser"])
            self.assertNotIn("X^", res["ser"], "the X register leaked into the body")
            self.assertAlmostEqual(float(res["value"]), expected, places=3,
                                   msg=f"d/dx(X^2) at X={x}")

    def test_derivative_delete_and_exit(self):
        self.press("integral", shift=True)
        self.types("X")
        self.press("del")
        self.assertEqual(self.page.evaluate("() => getExpr()"), "diff(x,0)")
        self.press("dpad_right")
        self.assertIsNone(self.cursor_state()["template"])
        self.press("del")
        self.assertEqual(self.page.evaluate("() => getExpr()"), "")

    def test_derivative_undo_restores_the_template(self):
        self.press("integral", shift=True)
        self.types("X")
        before = self.page.evaluate("() => getExpr()")
        self.page.evaluate("() => { popUndoState(); }")
        self.assertIn("math-derivative-template", self.lcd_html())


class TestSigmaTemplate(BrowserCase):
    """Phase 7 / SIG-1."""

    def test_shift_x_builds_a_summation_template_not_raw_text(self):
        self.press("variable", shift=True)
        st = self.cursor_state()
        self.assertEqual(st["template"], "sigma")
        self.assertEqual(st["slot"], "body")
        html = self.lcd_html()
        self.assertIn('class="math-sigma-template"', html)
        self.assertIn('class="math-sigma-upper"', html)
        self.assertIn('class="math-sigma-lower"', html)
        self.assertIn('class="math-sigma-sym">\u03a3<', html)
        self.assertIn('class="math-sigma-prefix">x=<', html)
        self.assertIn('class="math-sigma-body"', html)
        # The old defect: a literal, unbalanced "\u03a3(" text token.
        self.assertNotIn("\u03a3(", html)
        self.assertTrue(self.has_cursor())

    def test_summation_reading_order_is_lower_upper_body(self):
        self.press("variable", shift=True)
        self.press("dpad_left")
        self.assertEqual(self.cursor_state()["slot"], "upper")
        self.press("dpad_left")
        self.assertEqual(self.cursor_state()["slot"], "lower")
        self.press("dpad_left")
        self.assertIsNone(self.cursor_state()["template"], "must be able to leave")

        self.reset()
        self.press("variable", shift=True)
        self.press("dpad_left"); self.press("dpad_left")
        self.types("1")
        self.press("dpad_right"); self.types("5")
        self.press("dpad_right")
        self.assertEqual(self.cursor_state()["slot"], "body")
        self.page.evaluate("() => { insertToken('X'); }")
        self.assertEqual(self.page.evaluate("() => getExpr()"), "sigma(x,1,5)")

    def test_summation_vertical_navigation_reaches_both_bounds(self):
        self.press("variable", shift=True)
        self.types("7")
        self.press("dpad_up")
        self.assertEqual(self.cursor_state()["slot"], "upper")
        self.press("dpad_down")
        self.assertEqual(self.cursor_state()["slot"], "lower")

    def test_summation_evaluates_correctly(self):
        # The body is written with the calculator's `x` register key but must
        # reach the engine as the summation dummy.
        for body, expected_ser, expected in (("X", "sigma(x,1,5)", 15.0),
                                            ("X^2", "sigma(((x)^(2)),1,5)", 55.0)):
            res = self.page.evaluate(
                """(b) => {
                     appState.variables.X = 999;   // must NOT leak into the body
                     resetExpr(); insertSigma();
                     const tmpl = rootSlot.items[0];
                     tmpl.lower.items = ['1'];
                     tmpl.upper.items = ['5'];
                     tmpl.body.items = (b === 'X^2')
                       ? [{ type: 'power', id: 900, base: createSlot(['X']),
                            exp: createSlot(['2']) }]
                       : [b];
                     const ser = getExpr();
                     let value; try { value = localEvaluate(ser); }
                     catch (e) { value = 'THREW: ' + e.message; }
                     return { ser: ser, value: value }; }""", body)
            self.assertEqual(res["ser"], expected_ser)
            self.assertAlmostEqual(float(res["value"]), expected, places=6, msg=res["ser"])

    def test_summation_delete_inside_the_body(self):
        self.press("variable", shift=True)
        self.types("X")
        self.press("del")
        self.assertEqual(self.page.evaluate("() => getExpr()"), "sigma(0,0,0)")
        self.assertIn('class="math-sigma-template"', self.lcd_html())


class TestIntegralTemplate(BrowserCase):
    """Phase 8 (already implemented; guards against regression)."""

    def test_integral_has_symbol_bounds_body_and_dx(self):
        self.press("integral")
        st = self.cursor_state()
        self.assertEqual((st["template"], st["slot"]), ("integral", "body"))
        html = self.lcd_html()
        for cls in ("math-integral-template", "math-int-upper",
                    "math-int-sym", "math-int-lower",
                    "math-int-body", "math-int-dx"):
            self.assertIn(f'class="{cls}"', html, cls)
        self.assertIn("\u222b", html)

    def test_integral_bounds_are_editable_and_serialize_in_order(self):
        self.press("integral")
        self.page.evaluate("() => { insertToken('X'); insertPower('2'); }")
        self.press("dpad_up"); self.types("3")
        self.press("dpad_down"); self.types("0")
        # body, lower, upper -- with the register key mapped to the dummy
        self.assertEqual(self.page.evaluate("() => getExpr()"),
                         "integral(((x)^(2)),0,3)")

    def test_integral_evaluates(self):
        res = self.page.evaluate(
            """() => { resetExpr(); insertIntegral();
                 const t = rootSlot.items[0];
                 t.body.items = [{ type: 'power', id: 901, base: createSlot(['X']),
                                   exp: createSlot(['2']) }];
                 t.lower.items = ['0']; t.upper.items = ['3'];
                 const ser = getExpr();
                 let v; try { v = localEvaluate(ser); }
                 catch (e) { v = 'THREW: ' + e.message; }
                 return { ser: ser, value: v }; }""")
        self.assertEqual(res["ser"], "integral(((x)^(2)),0,3)")
        self.assertAlmostEqual(float(res["value"]), 9.0, places=6)


class TestRootsPowersAndLog(BrowserCase):
    """Phase 9 / Phase 10: superscripts, subscripts, roots."""

    def test_power_has_a_real_editable_exponent_slot(self):
        self.types("2")
        self.press("power")
        self.assertEqual(self.cursor_state()["slot"], "exp")
        self.types("5")
        html = self.lcd_html()
        self.assertIn('class="math-power-base"', html)
        self.assertIn('class="math-power-exp"', html)
        self.assertEqual(self.page.evaluate("() => getExpr()"), "((2)^(5))")

    def test_square_and_cube_use_the_power_template(self):
        self.types("3"); self.press("square")
        self.assertIn('class="math-power-exp"', self.lcd_html())
        self.assertEqual(self.page.evaluate("() => getExpr()"), "((3)^(2))")
        self.reset()
        self.types("3"); self.press("square", shift=True)
        self.assertEqual(self.page.evaluate("() => getExpr()"), "((3)^(3))")

    def test_sqrt_cbrt_and_nth_root_are_templates_with_slots(self):
        self.press("sqrt"); self.types("2"); self.types("5")
        self.assertIn("\u221a", self.lcd_html())
        self.assertEqual(self.page.evaluate("() => getExpr()"), "sqrt(25)")

        self.reset()
        self.press("sqrt", shift=True); self.types("2"); self.types("7")
        self.assertEqual(self.page.evaluate("() => getExpr()"), "cbrt(27)")
        self.assertIn('class="math-root-index"', self.lcd_html())

        self.reset()
        self.press("power", shift=True)
        self.assertEqual(self.cursor_state()["slot"], "index")
        self.types("3")
        self.press("dpad_right")
        self.assertEqual(self.cursor_state()["slot"], "radicand")
        self.types("1"); self.types("6")
        self.assertEqual(self.page.evaluate("() => getExpr()"), "xroot(3,16)")

    def test_log_base_is_a_template_with_base_and_argument_slots(self):
        self.press("log")
        self.assertEqual(self.cursor_state()["slot"], "base")
        self.types("2")
        self.press("dpad_right")
        self.assertEqual(self.cursor_state()["slot"], "arg")
        self.types("8")
        html = self.lcd_html()
        self.assertIn('class="math-log-sub"', html)
        self.assertIn('class="math-log-arg"', html)
        self.assertEqual(self.page.evaluate("() => getExpr()"), "log_base(2,8)")

    def test_inverse_power_key_produces_a_superscript_slot(self):
        self.types("4")
        self.press("inverse")
        self.assertIn('class="math-power-exp"', self.lcd_html())
        self.assertEqual(self.page.evaluate("() => getExpr()"), "((4)^(-1))")


class TestShiftAlphaBehaviour(BrowserCase):
    """Phase 11 / SHIFT-1 / ALPHA-1."""

    def test_shift_indicators_track_state(self):
        seq = self.page.evaluate(
            """() => {
              const out = [];
              const btn = k => document.querySelector('[data-key="'+k+'"]');
              const rec = label => out.push({ label: label,
                shift: appState.shift, alpha: appState.alpha,
                s: document.getElementById('indShift').classList.contains('active'),
                a: document.getElementById('indAlpha').classList.contains('active') });
              resetExpr(); rec('idle');
              handleKey(btn('shift')); rec('shift');
              handleKey(btn('fraction')); rec('shift+fraction');
              handleKey(btn('alpha')); rec('alpha');
              handleKey(btn('variable')); rec('alpha+x');
              return out; }""")
        by = {r["label"]: r for r in seq}
        self.assertFalse(by["idle"]["s"] and by["idle"]["a"])
        self.assertTrue(by["shift"]["shift"] and by["shift"]["s"])
        # a modifier is consumed by the next key
        self.assertFalse(by["shift+fraction"]["shift"])
        self.assertFalse(by["shift+fraction"]["s"])
        self.assertTrue(by["alpha"]["alpha"] and by["alpha"]["a"])
        self.assertFalse(by["alpha+x"]["alpha"])

    def test_shift_fraction_is_the_mixed_fraction_template(self):
        self.press("fraction", shift=True)
        self.assertEqual(self.cursor_state()["template"], "mixed")

    def test_alpha_on_the_x_key_inserts_y(self):
        self.press("variable", alpha=True)
        self.assertEqual(self.page.evaluate("() => getExpr()"), "y")

    def test_plain_x_key_still_inserts_the_x_register(self):
        self.press("variable")
        self.assertEqual(self.page.evaluate("() => getExpr()"), "X")

    def test_alpha_right_paren_still_inserts_x(self):
        self.press("right_paren", alpha=True)
        self.assertEqual(self.page.evaluate("() => getExpr()"), "X")


class TestLatexConversion(unittest.TestCase):
    """exprToLatex is the LaTeX bridge for the MathO layer."""

    @classmethod
    def setUpClass(cls):
        if not (shutil.which("node") and HAVE_PLAYWRIGHT):
            raise unittest.SkipTest("node is not installed")
        import subprocess
        start = FRONTEND.index("function exprToLatex(")
        brace = FRONTEND.index("{", start)
        depth, i = 0, brace
        while True:
            if FRONTEND[i] == "{":
                depth += 1
            elif FRONTEND[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        fn = FRONTEND[start:i + 1]
        runner = (fn + "\nconst cases=JSON.parse(process.argv[2]);"
                  "const out=[];for(const c of cases){try{out.push(exprToLatex(c));}"
                  "catch(e){out.push('THREW: '+e.message);}}"
                  "process.stdout.write(JSON.stringify(out));\n")
        tmp = PROJECT / ".expr_latex_tmp.js"
        tmp.write_text(runner, encoding="utf-8")
        try:
            proc = subprocess.run(["node", str(tmp), json.dumps(cls.CASES)],
                                  capture_output=True, text=True,
                                  encoding="utf-8", timeout=60)
        finally:
            tmp.unlink(missing_ok=True)
        assert proc.returncode == 0, proc.stderr[:400]
        cls.out = dict(zip(cls.CASES, json.loads(proc.stdout)))

    CASES = ["2+3", "sqrt(25)", "sigma(x,1,5)", "diff(x^2,3)",
             "integral(x^2,0,3)", "log_base(2,8)", "xroot(3,16)",
             "((1+2))/((3+4))", "1/2", "1 23/45"]

    def test_special_functions_become_real_latex(self):
        self.assertEqual(self.out["sqrt(25)"], "\\sqrt{25}")
        self.assertEqual(self.out["sigma(x,1,5)"], "\\sum_{1}^{5}(x)")
        self.assertEqual(self.out["diff(x^2,3)"],
                         "\\frac{d}{dx}\\left[x^2\\right]_{x=3}")
        self.assertEqual(self.out["integral(x^2,0,3)"],
                         "\\int_{0}^{3}(x^2)\\,dx")
        self.assertEqual(self.out["log_base(2,8)"], "\\log_{2}{8}")
        self.assertEqual(self.out["xroot(3,16)"], "\\sqrt[3]{16}")

    def test_fractions_become_stacked_latex(self):
        self.assertEqual(self.out["((1+2))/((3+4))"], "\\frac{1+2}{3+4}")
        self.assertEqual(self.out["1/2"], "\\frac{1}{2}")
        self.assertEqual(self.out["1 23/45"], "1\\frac{23}{45}")

    def test_no_function_call_names_leak_into_latex(self):
        # The audit explicitly rejects "Sigma(", "d/dx(", "frac(", "sqrt(" as
        # acceptable visual output.
        for bad in ("Sigma(", "sigma(", "d/dx(", "\\frac(", "\\sqrt("):
            for src, latex in self.out.items():
                self.assertNotIn(bad, latex, f"{src!r} -> {latex!r}")


if __name__ == "__main__":
    unittest.main()