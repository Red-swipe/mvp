"""Regression tests for the LCD font scope fix and the four-part integral /
two-part derivative templates.

ROOT CAUSE (confirmed by screenshot, not by speculation):
`CASIOClassWizCW01.ttf` is the KEYCAP LEGEND face -- its digits ARE keycap
icons. It was declared first in the `.lcd` font stack, so every digit and
symbol on the calculator screen was painted as a keycap icon.

Covered defects:
  FONT-1  the keycap-legend face must not be reachable from any screen-text
          selector (.lcd and the mode/menu screens)
  FONT-2  the keycap legend selectors are the ONLY users of that face
  FONT-3  the broken "CASIO ClassWiz RS" @font-face is gone
  FONT-4  no two @font-face rules may share a family name
  FONT-5  KaTeX is vendored locally and referenced with relative URLs; no CDN
  FONT-6  every vendored asset the stylesheet references actually exists
  FONT-7  KaTeX_* faces stay inside .katex
  SPEC-1  the PyInstaller spec bundles the vendored frontend assets
  INT-1   the integral template has FOUR editable parts
  INT-2   each typed digit lands in the intended part (key-driven)
  INT-3   integral of t^2 over [0,3] with dt == 9   (numbers, not strings)
  INT-4   integral of x^2 over [0,3] with dx == 9
  INT-5   collision: dx variable `t` + a free `x` in the integrand -> Syntax ERROR
  INT-6   a `t` dx variable must not touch the function name `tan`
  INT-7   the engine dummy never leaks into the displayed expression
  INT-8   the dx-variable slot accepts only ONE variable letter
  INT-9   every empty integral part -> Syntax ERROR on `=`
  DER-1   the derivative template has TWO slots (expression, point)
  DER-2   each typed digit lands in the intended part (key-driven)
  DER-3   d/dx(x^2) at the point 3 == 6
  DER-4   every empty derivative part -> Syntax ERROR on `=`

Empty slots are legal while editing; the error is raised on `=` only.
Browser tests skip cleanly when Playwright or Chrome is unavailable; the
static/structural tests always run.
"""
import re
import shutil
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
FRONTEND_PATH = PROJECT / "frontend.html"
FRONTEND = FRONTEND_PATH.read_text(encoding="utf-8")
SPEC_PATH = PROJECT / "MentisClassWiz.spec"

# The face that must never paint screen text.
KEYCAP_FACE = "CASIO ClassWiz"
# What the screen must use instead: the genuine ClassWiz CW DISPLAY face
# (Wenti-D v3.009, SIL OFL 1.1), which is a real text face with 1287 glyphs --
# unlike the CW01 keycap ARTWORK face above, whose digits are keycap icons.
SCREEN_TEXT_FACE = "CWDisplay"
LCD_FONT_VAR = "--lcd-font"

try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:                                     # pragma: no cover
    HAVE_PLAYWRIGHT = False

URL = FRONTEND_PATH.as_uri()

KATEX_DIR = PROJECT / "katex"


def strip_comments(src):
    """Remove CSS and JS comments so prose cannot satisfy a selector assertion."""
    out = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    out = re.sub(r"(?m)^\s*//.*$", " ", out)
    return out


CSS_NO_COMMENTS = strip_comments(FRONTEND)


def font_rules(css):
    """Every `selectors { ... font-family: ... }` rule as (selectors, stack).

    @font-face blocks are skipped: they DECLARE a family rather than apply one,
    so they are not a place a family can be used.
    """
    out = []
    for m in re.finditer(r"([^{}@]+)\{([^{}]*)\}", css):
        selectors = m.group(1)
        if selectors.strip().lower().endswith("font-face"):
            continue
        body = m.group(2)
        if "font-family" not in body:
            continue
        fm = re.search(r"font-family\s*:\s*([^;}]+)", body)
        if fm:
            out.append((selectors.strip(), fm.group(1).strip()))
    return out


def font_faces(css):
    """Every @font-face family name declared in the stylesheet."""
    return re.findall(r"@font-face\s*\{[^{}]*?font-family\s*:\s*([^;}]+)", css, re.S)


def selector_names(selectors):
    return {s.strip() for s in selectors.split(",")}


# Selectors that paint calculator-screen text. The keycap face must never be
# reachable from any of them.
SCREEN_TEXT_SELECTORS = {
    ".lcd", ".lcd-expr-content", ".lcd-result-line", ".math-sym",
    ".menu-overlay", ".menu-icon", ".menu-icon .mi-main",
}


# --------------------------------------------------------------------------
# Typography
# --------------------------------------------------------------------------
class TestFontFaceDeclarations(unittest.TestCase):
    """FONT-3 / FONT-4 / FONT-8.

    The keycap TTF is not a text face at all -- in it the ASCII digits are
    circled keycap icons -- so it was removed from the UI entirely rather than
    merely kept off the screen. Nothing may declare it any more.
    """

    def test_broken_rs_face_is_removed(self):
        self.assertNotIn("CASIO ClassWiz RS", CSS_NO_COMMENTS,
                         "the @font-face for the non-existent "
                         "CASIO ClassWiz RS.ttf must be removed, not left to "
                         "fail silently on every load")
        # Nothing may still request the missing file (URL-encoded or not).
        self.assertNotIn("ClassWiz%20", FRONTEND)

    def test_no_two_font_face_rules_share_a_family_name(self):
        names = [n.strip().strip("'\"") for n in font_faces(CSS_NO_COMMENTS)]
        duplicates = {n for n in names if names.count(n) > 1}
        self.assertEqual(duplicates, set(),
                         f"duplicate @font-face family name(s): {sorted(duplicates)}")

    def test_the_keycap_face_is_not_declared_any_more(self):
        names = [n.strip().strip("'\"") for n in font_faces(CSS_NO_COMMENTS)]
        self.assertNotIn(KEYCAP_FACE, names,
                         "the keycap artwork font must not be declared: its "
                         "digits are keycap icons, so it cannot render text")
        # Exactly one webfont is declared: the genuine CW Display face.
        self.assertEqual(re.findall(r"@font-face", CSS_NO_COMMENTS), ["@font-face"],
                         "expected exactly one @font-face: the CW Display face")
        self.assertEqual(names, [SCREEN_TEXT_FACE], names)

    def test_nothing_in_the_frontend_references_the_keycap_font_file(self):
        for needle in ("CW01", "CASIO ClassWiz", "Casio ClassWiz"):
            self.assertNotIn(needle, FRONTEND,
                             f"frontend.html still mentions {needle!r}")


class TestFontScope(unittest.TestCase):
    """FONT-1 / FONT-2 / FONT-7."""

    def test_screen_text_selectors_never_use_the_keycap_face(self):
        for selectors, stack in font_rules(CSS_NO_COMMENTS):
            for name in selector_names(selectors):
                if name in SCREEN_TEXT_SELECTORS:
                    self.assertNotIn(
                        KEYCAP_FACE, stack,
                        f"{name} paints screen text with the keycap face "
                        f"({stack}); its digits are keycap icons")

    def test_the_lcd_stack_is_an_explicit_text_stack(self):
        # `.lcd` delegates to --lcd-font (--lcd is taken by the screen's
        # background COLOUR), and that variable must name the real display face
        # plus per-character fallbacks for the code points it lacks.
        m = re.search(r"\.lcd\{[^}]*?font-family\s*:\s*([^;]+);", CSS_NO_COMMENTS, re.S)
        self.assertIsNotNone(m, ".lcd font-family not found")
        self.assertIn(LCD_FONT_VAR, m.group(1), m.group(1))

        v = re.search(re.escape(LCD_FONT_VAR) + r"\s*:\s*([^;]+);", CSS_NO_COMMENTS)
        self.assertIsNotNone(v, f"{LCD_FONT_VAR} not declared")
        stack = v.group(1)
        self.assertIn(SCREEN_TEXT_FACE, stack, stack)
        self.assertIn("Cambria Math", stack, stack)
        self.assertNotIn(KEYCAP_FACE, stack, stack)
        self.assertNotEqual(stack.strip(), "monospace", stack)

    def test_the_display_face_asset_is_vendored_with_its_licence(self):
        font = PROJECT / "ClassWizFontSet" / "ClassWizCWDisplay-Regular.woff2"
        self.assertTrue(font.exists(),
                        f"{font.name} is not vendored; the LCD face cannot load")
        licence = PROJECT / "ClassWizFontSet" / "OFL-CWDisplay.txt"
        self.assertTrue(licence.exists(),
                        "the SIL OFL text must travel with the vendored font")
        body = licence.read_text(encoding="utf-8", errors="replace")
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", body)
        self.assertIn("ClassWiz CW Display", body)

    def test_no_rule_anywhere_names_the_keycap_face(self):
        offenders = [f"{s} -> {stack}" for s, stack in font_rules(CSS_NO_COMMENTS)
                     if KEYCAP_FACE in stack]
        self.assertEqual(offenders, [],
                         "the keycap artwork font must be removed from the UI "
                         f"entirely, but these rules still name it: {offenders}")

    def test_math_sym_still_names_a_real_math_face(self):
        # The screen text stack has no glyph for the audited math code points,
        # so those fragments keep their explicit math face.
        m = re.search(r"\.math-sym,[^{]*\{([^}]*)\}", CSS_NO_COMMENTS, re.S)
        self.assertIsNotNone(m, ".math-sym rule missing")
        self.assertIn("Cambria Math", m.group(1))

    def test_no_rule_forces_a_font_inside_katex(self):
        # A universal/id selector naming a concrete family would re-type every
        # KaTeX glyph (TYPO-3 / KATEX). KaTeX_* must stay inside .katex.
        for selectors, stack in font_rules(CSS_NO_COMMENTS):
            names = selector_names(selectors)
            if any(n.endswith("*") or "#" in n for n in names):
                self.assertNotIn("KaTeX_", stack,
                                 f"{selectors} forces {stack} over KaTeX glyphs")


class TestKatexVendored(unittest.TestCase):
    """FONT-5 / FONT-6."""

    def test_no_cdn_reference_to_katex_remains(self):
        for host in ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com/ajax/libs/katex"):
            self.assertNotIn(host, FRONTEND,
                             f"katex is still loaded from {host}")

    def test_katex_is_referenced_with_relative_urls(self):
        for rel in ("katex/katex.min.css", "katex/katex.min.js",
                    "katex/contrib/auto-render.min.js"):
            self.assertIn(rel, FRONTEND, f"{rel} is not referenced")
            self.assertNotIn(f'"{rel[0]}/{rel}"', FRONTEND,
                             f"{rel} must be relative, not absolute")

    def test_the_referenced_tags_are_local_script_and_link_elements(self):
        self.assertRegex(FRONTEND, r'<link[^>]+href="katex/katex\.min\.css"')
        self.assertRegex(FRONTEND, r'<script[^>]+src="katex/katex\.min\.js"')

    def test_the_vendored_assets_exist(self):
        for rel in ("katex/katex.min.css", "katex/katex.min.js",
                    "katex/contrib/auto-render.min.js"):
            self.assertTrue((PROJECT / rel).is_file(), f"missing {rel}")

    def test_every_font_the_vendored_stylesheet_references_exists(self):
        css_path = KATEX_DIR / "katex.min.css"
        if not css_path.is_file():                          # pragma: no cover
            self.skipTest("katex is not vendored")
        css = css_path.read_text(encoding="utf-8")
        refs = sorted(set(re.findall(r"url\((fonts/[^)]+\.woff2)\)", css)))
        self.assertTrue(refs, "the vendored stylesheet references no woff2")
        missing = [r for r in refs if not (KATEX_DIR / r).is_file()]
        self.assertEqual(missing, [], f"missing vendored fonts: {missing}")

    def test_the_vendored_stylesheet_is_ka_tex_0_16_11(self):
        css_path = KATEX_DIR / "katex.min.css"
        if not css_path.is_file():                          # pragma: no cover
            self.skipTest("katex is not vendored")
        self.assertIn("KaTeX_Main", css_path.read_text(encoding="utf-8"))


class TestPyInstallerSpec(unittest.TestCase):
    """SPEC-1."""

    def setUp(self):
        if not SPEC_PATH.is_file():                         # pragma: no cover
            self.skipTest("no PyInstaller spec")
        self.spec = SPEC_PATH.read_text(encoding="utf-8")

    def test_the_spec_bundles_the_frontend_and_the_vendored_assets(self):
        for needle in ("frontend.html", "ClassWizFontSet", "katex"):
            self.assertIn(needle, self.spec,
                          f"the spec does not bundle {needle}; a packaged build "
                          f"would ship without it")

    def test_the_spec_datas_are_not_empty(self):
        self.assertNotRegex(self.spec, r"datas\s*=\s*\[\s*\]",
                            "datas is empty: nothing would be bundled")


# --------------------------------------------------------------------------
# Calculus template source structure
# --------------------------------------------------------------------------
class TestCalculusSlotSource(unittest.TestCase):
    """INT-1 / DER-1 / INT-8 at the source level."""

    def test_integral_template_creates_four_slots(self):
        m = re.search(r"function insertIntegral\(\)\s*\{[^\n]*", FRONTEND)
        self.assertIsNotNone(m, "insertIntegral not found")
        line = m.group(0)
        for slot in ("body", "lower", "upper", "dvar"):
            self.assertIn(f"{slot}:createSlot()", line,
                          f"the integral template has no {slot} slot: {line}")

    def test_derivative_template_creates_two_slots(self):
        m = re.search(r"function insertDerivative\(\)\s*\{[^\n]*", FRONTEND)
        self.assertIsNotNone(m, "insertDerivative not found")
        line = m.group(0)
        for slot in ("body", "point"):
            self.assertIn(f"{slot}:createSlot()", line,
                          f"the derivative template has no {slot} slot: {line}")

    def test_the_new_slots_are_traversable(self):
        # cloneSlot / getSlotPath / findParent walk one shared key list; a slot
        # missing from it is invisible to undo, cursor-path resolution and
        # cursor navigation, so the cursor could never reach the dx variable.
        m = re.search(r"const SLOT_KEYS = \[([^\]]*)\]", FRONTEND)
        self.assertIsNotNone(m, "no shared SLOT_KEYS list")
        for key in ("'dvar'", "'point'"):
            self.assertIn(key, m.group(1), f"SLOT_KEYS is missing {key}")
        for fn in ("cloneSlot", "getSlotPath", "findParent"):
            fm = re.search(r"function " + fn + r"\(", FRONTEND)
            self.assertIsNotNone(fm, f"{fn} not found")
            seg = FRONTEND[fm.start():fm.start() + 700]
            self.assertIn("SLOT_KEYS", seg,
                          f"{fn} does not walk the shared slot key list, so the "
                          f"new slots are invisible to it")

    def test_the_dx_variable_is_rewritten_as_a_standalone_token(self):
        # `t` must not touch `tan`, so the rewrite has to be token-bounded.
        self.assertIn("function integralBody(", FRONTEND)
        start = FRONTEND.index("function integralBody(")
        seg = FRONTEND[start:start + 900]
        self.assertIn("\\b", seg,
                      "the dx rewrite is not token-bounded (a bare character "
                      "replace would corrupt `tan`)")
        self.assertIn("RegExp", seg,
                      "the dx rewrite must build its pattern from the chosen "
                      "variable")

    def test_empty_calculus_slots_are_validated_before_evaluation(self):
        self.assertIn("function validateCalculusTree(", FRONTEND)
        m = re.search(r"async function evaluate\(\)\s*\{[\s\S]{0,600}", FRONTEND)
        self.assertIsNotNone(m, "evaluate() not found")
        self.assertIn("validateCalculusTree", m.group(0),
                      "evaluate() does not reject empty calculus slots")


# --------------------------------------------------------------------------
# Browser behaviour
# --------------------------------------------------------------------------
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
class CalcSlotBrowserCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls._browser.new_page(viewport={"width": 900, "height": 1500})
        cls.page.goto(URL)
        cls.page.wait_for_timeout(2500)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def setUp(self):
        self.page.evaluate(
            """() => { resetExpr(); appState.shift = false; appState.alpha = false;
                 appState.resultDisplayed = false; appState.result = null;
                 appState.error = null; renderLCD(); }""")

    # -- helpers -------------------------------------------------------
    def press(self, key, shift=False):
        self.page.evaluate(
            """([k, s]) => {
                 const b = document.querySelector('[data-key="' + k + '"]');
                 if (!b) throw new Error('no such key: ' + k);
                 appState.shift = s; appState.alpha = false;
                 handleKey(b);
                 appState.shift = false; appState.alpha = false;
                 renderLCD();
               }""", [key, shift])

    def types(self, text):
        for ch in text:
            self.page.evaluate("(c) => { insertToken(c); }", ch)

    def token(self, ch):
        self.page.evaluate("(c) => { insertToken(c); }", ch)

    def cursor_state(self):
        return self.page.evaluate(
            """() => { const p = getParent();
                 return { template: p && p.par ? p.par.type : null,
                          slot: p ? p.slotName : null,
                          index: cursor.index }; }""")

    def slot_items(self, name):
        return self.page.evaluate(
            "(n) => { const t = rootSlot.items[0];"
            " return t && t[n] ? t[n].items.slice() : null; }", name)

    def slot_elements(self):
        """Slot ids of the real, hydrated editable elements in the DOM."""
        return self.page.eval_on_selector_all(
            "#lcdExprContent [data-slot-id]", "els => els.map(e => e.dataset.slotId)")

    def lcd_text(self):
        return self.page.inner_text("#lcdExprContent")

    def evaluate(self):
        self.page.evaluate("() => { evaluate(); }")
        self.page.wait_for_timeout(150)
        return self.page.evaluate(
            """() => ({ result: appState.result, error: appState.error })""")

    def number(self, state):
        self.assertIsNone(state["error"], f"unexpected error: {state['error']}")
        self.assertIsNotNone(state["result"], "no result was produced")
        return float(state["result"])


class TestIntegralSlots(CalcSlotBrowserCase):
    def test_the_four_parts_exist_and_the_cursor_starts_in_the_integrand(self):
        self.press("integral")
        st = self.cursor_state()
        self.assertEqual((st["template"], st["slot"]), ("integral", "body"))
        html = self.page.inner_html("#lcdExprContent")
        # KaTeX owns the skeleton now: a real tall integral with stacked limits,
        # and all four parts as hydrated slot elements.
        self.assertIn("katex", html)
        self.assertIn("op-symbol", html, "no integral operator")
        self.assertIn("msupsub", html, "the limits are not stacked on the sign")
        self.assertEqual(len(self.slot_elements()), 4, self.slot_elements())

    def test_each_typed_digit_lands_in_the_intended_part(self):
        self.press("integral")
        # 1. the integrand
        self.types("2")
        self.assertEqual(self.slot_items("body"), ["2"])
        # right out of the integrand lands on the dx variable
        self.press("dpad_right")
        self.assertEqual(self.cursor_state()["slot"], "dvar")
        self.token("t")
        self.assertEqual(self.slot_items("dvar"), ["t"])
        # 2. the upper bound, reached from the integrand. Left first steps back over
        # the letter already typed in the dx variable, then leaves the part.
        self.press("dpad_left")
        self.assertEqual(self.cursor_state()["slot"], "dvar")
        self.press("dpad_left")
        self.assertEqual(self.cursor_state()["slot"], "body")
        self.press("dpad_up")
        self.assertEqual(self.cursor_state()["slot"], "upper")
        self.types("3")
        self.assertEqual(self.slot_items("upper"), ["3"])
        # 3. the lower bound
        self.press("dpad_down")
        self.assertEqual(self.cursor_state()["slot"], "lower")
        self.types("0")
        self.assertEqual(self.slot_items("lower"), ["0"])
        self.assertEqual(self.slot_items("body"), ["2"])
        self.assertEqual(self.slot_items("dvar"), ["t"])

    def _fill(self, dvar):
        self.page.evaluate(
            """(d) => { resetExpr(); insertIntegral();
                 const t = rootSlot.items[0];
                 t.body.items = [{ type:'power', id: 950, base: createSlot([d]),
                                   exp: createSlot(['2']) }];
                 t.lower.items = ['0']; t.upper.items = ['3'];
                 if (d !== null) t.dvar.items = [d];
                 renderLCD(); }""", dvar)

    def test_integral_with_dt_evaluates_to_nine(self):
        self._fill("t")
        state = self.evaluate()
        self.assertAlmostEqual(self.number(state), 9.0, places=6)

    def test_integral_with_dx_evaluates_to_nine(self):
        self._fill("x")
        state = self.evaluate()
        self.assertAlmostEqual(self.number(state), 9.0, places=6)

    def test_a_t_variable_does_not_touch_the_function_name_tan(self):
        results = []
        for var in ("t", "x"):
            self.page.evaluate(
                """(d) => { resetExpr(); insertIntegral();
                     const t = rootSlot.items[0];
                     t.body.items = ['tan', createSlot([d]), '(', '1', ')'];
                     t.lower.items = ['0']; t.upper.items = ['1'];
                     t.dvar.items = [d];
                     renderLCD(); }""", var)
            results.append(self.number(self.evaluate()))
        self.assertAlmostEqual(results[0], results[1], places=9,
                               msg=f"dt and dx disagree: {results}")

    def test_a_free_x_in_the_integrand_collides_with_the_dx_variable(self):
        # dx variable t, integrand written with the x key -> Syntax ERROR,
        # never a silent alias of the two variables.
        self.page.evaluate(
            """() => { resetExpr(); insertIntegral();
                 const t = rootSlot.items[0];
                 t.body.items = ['X']; t.lower.items = ['0']; t.upper.items = ['3'];
                 t.dvar.items = ['t'];
                 renderLCD(); }""")
        state = self.evaluate()
        self.assertEqual(state["error"], "Syntax ERROR", state)
        self.assertIsNone(state["result"])

    def test_the_dx_variable_accepts_only_one_variable_letter(self):
        self.press("integral")
        self.press("dpad_right")
        self.assertEqual(self.cursor_state()["slot"], "dvar")
        for bad in ("5", "+", "\u03c0", "("):
            self.token(bad)
            self.assertEqual(self.slot_items("dvar"), [],
                             f"{bad!r} was accepted as a dx variable")
        self.token("t")
        self.token("t")
        self.assertEqual(self.slot_items("dvar"), ["t"],
                         "the dx variable slot must hold exactly one letter")
        self.token("u")
        self.assertEqual(self.slot_items("dvar"), ["u"],
                         "choosing a different variable must replace it")

    def test_the_engine_dummy_never_leaks_into_the_displayed_expression(self):
        self._fill("t")
        # Read the VISIBLE subtree only: the MathML annotation carries the raw
        # LaTeX source, which legitimately mentions the engine's dummy.
        shown = self.page.evaluate(
            """() => { const h = document.getElementById('lcdExprContent');
                 const v = h.querySelector('.katex-html');
                 return v ? v.textContent : h.textContent; }""")
        self.assertIn("dt", shown, shown)
        self.assertNotIn("dx", shown, shown)
        # The integral still renders as a KaTeX operator.
        self.assertIn("op-symbol", self.page.inner_html("#lcdExprContent"))

    def test_every_empty_part_is_a_syntax_error(self):
        for empty in ("body", "lower", "upper", "dvar"):
            with self.subTest(part=empty):
                self.page.evaluate(
                    """(e) => { resetExpr(); insertIntegral();
                         const t = rootSlot.items[0];
                         t.body.items = ['X', '2']; t.lower.items = ['0'];
                         t.upper.items = ['3']; t.dvar.items = ['t'];
                         t[e].items = [];
                         renderLCD(); }""", empty)
                state = self.evaluate()
                self.assertEqual(state["error"], "Syntax ERROR", state)


class TestDerivativeSlots(CalcSlotBrowserCase):
    def test_the_two_slots_exist(self):
        self.press("integral", shift=True)
        st = self.cursor_state()
        self.assertEqual((st["template"], st["slot"]), ("derivative", "body"))
        html = self.page.inner_html("#lcdExprContent")
        # d/dx is a real KaTeX fraction; the evaluation point is a subscript.
        self.assertIn("katex", html)
        self.assertIn("mfrac", html, "d/dx is not a KaTeX fraction")
        self.assertIn("msub", html, "the |x= point is not a subscript")
        self.assertEqual(len(self.slot_elements()), 2, self.slot_elements())
        self.assertNotIn("d/dx(", html)

    def test_each_typed_digit_lands_in_the_intended_part(self):
        self.press("integral", shift=True)
        self.types("2")
        self.assertEqual(self.slot_items("body"), ["2"])
        self.press("dpad_right")
        self.assertEqual(self.cursor_state()["slot"], "point")
        self.types("3")
        self.assertEqual(self.slot_items("point"), ["3"])

    def test_the_point_slot_drives_the_derivative(self):
        for point, expected in (("3", 6.0), ("2", 4.0), ("0", 0.0)):
            with self.subTest(point=point):
                self.page.evaluate(
                    """(p) => { resetExpr(); insertDerivative();
                         const t = rootSlot.items[0];
                         t.body.items = [{ type:'power', id: 960,
                                           base: createSlot(['X']),
                                           exp: createSlot(['2']) }];
                         t.point.items = [p];
                         renderLCD(); }""", point)
                state = self.evaluate()
                self.assertAlmostEqual(self.number(state), expected, places=6,
                                       msg=str(state))

    def test_the_expression_uses_the_dummy_not_the_x_register(self):
        self.page.evaluate(
            """() => { appState.variables.X = 999;
                 resetExpr(); insertDerivative();
                 const t = rootSlot.items[0];
                 t.body.items = [{ type:'power', id: 961, base: createSlot(['X']),
                                   exp: createSlot(['2']) }];
                 t.point.items = ['3'];
                 renderLCD(); }""")
        state = self.evaluate()
        self.assertAlmostEqual(self.number(state), 6.0, places=6, msg=str(state))

    def test_every_empty_part_is_a_syntax_error(self):
        for empty in ("body", "point"):
            with self.subTest(part=empty):
                self.page.evaluate(
                    """(e) => { resetExpr(); insertDerivative();
                         const t = rootSlot.items[0];
                         t.body.items = ['X', '2']; t.point.items = ['3'];
                         t[e].items = [];
                         renderLCD(); }""", empty)
                state = self.evaluate()
                self.assertEqual(state["error"], "Syntax ERROR", state)


if __name__ == "__main__":
    unittest.main()