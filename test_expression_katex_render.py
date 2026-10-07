"""The editable expression line is typeset by KaTeX, with real slot elements.

Previously the input line was hand-built CSS boxes around literal glyphs while
only the RESULT line went through KaTeX, so a ClassWiz integral was a flex
column of divs rather than a tall sign with its limits above and below it.

Covered:
  KX-1   an inserted template renders a real `.katex` element in the expression
         area, with the proper glyph (.mop/.mop-op integrals, .mfrac, .mroot)
  KX-2   the integral is TALL with its limits stacked (msupsub over the sign),
         i.e. natural display rather than CSS boxes
  KX-3   all three editable integral slots are present, each a real element carrying a
         slot id
  KX-4   typing into each slot still produces the correct numeric result
  KX-5   the cursor survives KaTeX rendering, and slot entry still works
  KX-6   the placeholder/slot contract holds: one placeholder per leaf slot
  KX-7   nested templates still serialize (the model is untouched)

Every assertion runs against the REAL rendered DOM in Chrome.
"""
import re
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


class TestExpressionKatexSource(unittest.TestCase):
    def test_the_expression_line_renders_through_katex(self):
        self.assertIn("function renderExprKatex(", FRONTEND)
        m = re.search(r"function renderLCD\(\)[\s\S]*?renderExprKatex\(\)", FRONTEND)
        self.assertIsNotNone(m, "renderLCD() does not call renderExprKatex()")

    def test_each_template_has_a_latex_skeleton(self):
        # 2600 chars: the \mathrm{d} comment above the derivative case pushed the
        # last few skeletons past the old window.
        raw = FRONTEND[FRONTEND.index("function itemLatex("):
                       FRONTEND.index("function itemLatex(") + 2600]
        # These skeletons live in JS string literals, so the source escapes each
        # backslash (`\\frac`). Collapse them so the needles below can be written
        # as plain TeX and a skeleton can never pass by matching half a backslash.
        seg = raw.replace("\\\\", "\\")
        for case, needle in (("integral", "\\int_{"), ("sigma", "\\sum_{"),
                             ("fraction", "\\frac{"), ("radical", "\\sqrt"),
                             ("cbrt", "\\sqrt[3]"),
                             ("derivative", "\\frac{\\mathrm{d}}{\\mathrm{d}x}"),
                             ("power", "}^{"), ("log", "\\log_")):
            self.assertIn(needle, seg, f"no LaTeX skeleton for {case}")

    def test_trust_is_enabled(self):
        # \class{}/\htmlId{} are the natural slot hooks and need trust:true,
        # so the option is set even though this build emits no hook for them.
        self.assertRegex(FRONTEND, r"trust:\s*true")


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
class ExprKatexBrowserCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls._browser.new_page(viewport={"width": 900, "height": 1600})
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

    def expr(self):
        return self.page.inner_html("#lcdExprContent")

    def state(self):
        return self.page.evaluate(
            """() => {
                 const host = document.getElementById('lcdExprContent');
                 const katex = host.querySelector('.katex');
                 const slots = Array.from(host.querySelectorAll('[data-slot-id]'))
                   .map(e => e.getAttribute('data-slot-id'));
                 return { hasKatex: !!katex,
                          slotIds: slots,
                          cursor: host.querySelectorAll('.lcd-cursor').length,
                          cursorPos: (() => { const p = getParent();
                                return { template: p && p.par ? p.par.type : null,
                                         slot: p ? p.slotName : null,
                                         index: cursor.index }; })(),
                          expr: getExpr() };
               }""")

    def slot_items(self, name):
        return self.page.evaluate(
            "(n) => { const t = rootSlot.items[0];"
            " return t && t[n] ? t[n].items.slice() : null; }", name)

    def evaluate(self):
        self.page.evaluate("() => { evaluate(); }")
        self.page.wait_for_timeout(200)
        return self.page.evaluate(
            "() => ({ result: appState.result, error: appState.error })")


class TestIntegralIsKatex(ExprKatexBrowserCase):
    """KX-1 / KX-2 / KX-3."""

    def test_the_integral_is_rendered_by_katex(self):
        self.press("integral")
        st = self.state()
        self.assertTrue(st["hasKatex"],
                        "the expression line is not typeset by KaTeX")
        html = self.expr()
        self.assertIn("katex", html)
        # A real integral operator (KaTeX emits .mop + .op-symbol for \int).
        self.assertIn("op-symbol", html,
                      "no integral operator in the KaTeX output")
        # The glyph must be KaTeX's own operator span, not a literal text node in
        # the old CSS boxes: the old renderer put it in .math-int-sym.
        self.assertNotIn("math-int-sym", html,
                         "the integral is still the old CSS/div glyph, not KaTeX")
        where = self.page.evaluate(
            """() => { const h = document.getElementById('lcdExprContent');
                 const op = h.querySelector('.op-symbol');
                 if (!op) return null;
                 return { text: op.textContent,
                          font: getComputedStyle(op).fontFamily }; }""")
        self.assertIsNotNone(where, "no .op-symbol operator span")
        self.assertIn("\u222b", where["text"], where)
        self.assertIn("KaTeX", where["font"],
                      f"the integral is not drawn in a KaTeX face: {where['font']}")

    def boxes_in_order(self, sel):
        """Slot elements under `sel`, sorted TOP TO BOTTOM (visual order).

        Deliberately not DOM order: KaTeX emits a fraction's denominator row
        first, so DOM order is the opposite of what the user sees.
        """
        return self.page.evaluate(
            """(s) => Array.from(document.querySelectorAll(
                 '#lcdExprContent ' + s + ' [data-slot-id]'))
               .map(e => ({ id: e.dataset.slotId,
                            text: e.textContent,
                            top: e.getBoundingClientRect().top }))
               .sort((a, b) => a.top - b.top)""", sel)

    def test_the_numerator_is_above_the_denominator(self):
        # KaTeX builds \\frac as a vlist whose DENOMINATOR row comes first in the
        # DOM, so a naive document-order hydration renders 1/2 as 2/1. Pin the
        # VISUAL order, which is what the user actually sees.
        self.press("fraction")
        self.types("1")
        self.press("dpad_right")
        self.types("2")
        boxes = self.boxes_in_order(".mfrac")
        self.assertEqual([b["text"] for b in boxes], ["1", "2"],
                         f"top-to-bottom should be 1 over 2, got {boxes}")
        self.assertLess(boxes[0]["top"], boxes[1]["top"],
                        "the numerator is not above the denominator")
        # ...and the model still says 1/2, i.e. only the DISPLAY was at risk.
        self.assertEqual(self.page.evaluate("() => getExpr()"), "((1)/(2))")

    def test_a_nested_fraction_keeps_visual_order(self):
        # outer fraction whose numerator is itself a fraction
        self.press("fraction")
        self.types("1")                      # outer numerator -> inner fraction
        self.page.evaluate("() => { insertFraction(); }")
        self.types("7")                      # inner numerator
        self.press("dpad_right")
        self.types("8")                      # inner denominator
        self.press("dpad_right")             # leave the inner fraction
        self.press("dpad_right")             # ...into the outer denominator
        self.types("9")                      # outer denominator
        boxes = self.boxes_in_order(".mfrac")
        self.assertEqual([b["text"] for b in boxes], ["7", "8", "9"],
                         f"top-to-bottom should be 7, 8, 9; got {boxes}")

    def test_a_mixed_number_keeps_visual_order(self):
        self.press("fraction", shift=True)   # mixed
        self.types("1")                       # whole
        self.press("dpad_right")
        self.types("2")                       # numerator
        self.press("dpad_right")
        self.types("3")                       # denominator
        boxes = self.boxes_in_order(".mfrac")
        self.assertEqual([b["text"] for b in boxes], ["2", "3"], boxes)
        whole = self.page.evaluate(
            """() => { const els = Array.from(document.querySelectorAll(
                 '#lcdExprContent [data-slot-id]'));
                 const e = els.find(x => x.textContent === '1');
                 return e ? Math.round(e.getBoundingClientRect().top) : null; }""")
        self.assertIsNotNone(whole, "the whole part is missing")
        self.assertGreater(whole, boxes[0]["top"],
                           "the whole part should sit below the fraction bar")

    def test_the_integral_is_tall_with_stacked_limits(self):
        self.press("integral")
        html = self.expr()
        # Natural display: the limits hang off the sign in a vlist (msupsub),
        # which is only what \int_{..}^{..} produces.
        self.assertIn("msupsub", html,
                      "the limits are not stacked above/below the sign")
        self.assertTrue(re.search(r'class="[^"]*\bvlist\b', html),
                        "no vlist: the limits are beside the sign, not on it")
        box = self.page.evaluate(
            """() => { const h = document.getElementById('lcdExprContent');
                 const op = h.querySelector('.op-symbol') ||
                            h.querySelector('.mop');
                 return op ? op.getBoundingClientRect().height : 0; }""")
        self.assertGreater(box, 14,
                           f"the integral sign is only {box}px tall; it is not "
                           f"set as a tall operator")

    def test_all_four_integral_slots_are_real_elements(self):
        self.press("integral")
        st = self.state()
        # body + lower + upper; dx is a fixed token
        self.assertEqual(len(st["slotIds"]), 3, st["slotIds"])
        self.assertEqual(len(set(st["slotIds"])), 3,
                         f"slot ids are not unique: {st['slotIds']}")
        html = self.expr()
        self.assertEqual(html.count("data-slot-id"), 3, html[:400])
        self.assertIn('data-fixed-token="true"', html)
        self.assertIn('>dx<', html)


class TestSlotsStillWork(ExprKatexBrowserCase):
    """KX-4 / KX-5 / KX-7."""

    def test_typing_into_each_integral_slot_yields_the_right_number(self):
        self.press("integral")
        self.page.evaluate("() => { insertToken('x'); }")
        self.page.evaluate("() => { insertPower('2'); }")
        self.assertEqual(self.slot_items("body")[0]["type"], "power")
        # navigate to the two bounds; dx is not focusable
        self.press("dpad_up"); self.types("3")
        self.assertEqual(self.slot_items("upper"), ["3"])
        self.press("dpad_down"); self.types("0")
        self.assertEqual(self.slot_items("lower"), ["0"])
        out = self.evaluate()
        self.assertIsNone(out["error"], out)
        self.assertAlmostEqual(float(out["result"]), 9.0, places=6)

    def test_the_three_editable_slots_are_reachable(self):
        for name, digit in (("body", "7"), ("upper", "3"), ("lower", "0")):
            with self.subTest(slot=name):
                self.setUp()
                self.press("integral")
                if name == "upper":
                    self.press("dpad_up")
                elif name == "lower":
                    self.press("dpad_down")
                self.types(digit)
                self.assertEqual(self.slot_items(name), [digit])

    def test_the_cursor_survives_katex_rendering(self):
        self.press("integral")
        st = self.state()
        self.assertEqual(st["cursor"], 1, "no cursor after inserting a template")
        self.assertEqual((st["cursorPos"]["template"], st["cursorPos"]["slot"]),
                         ("integral", "body"))
        self.types("5")
        self.assertEqual(self.state()["cursor"], 1,
                         "the cursor vanished while typing into a KaTeX slot")

    def test_a_cursor_in_a_slot_holding_templates_is_rendered(self):
        # A NON-leaf slot: the cursor sits in the root slot, which contains
        # templates, so there is no slot box for it. It is emitted as an extra
        # placeholder and hydrated into the cursor element. (Arrow keys cannot
        # reach this position -- left always dives into a template -- so it is
        # reached by typing, which is how a user gets there too.)
        self.press("fraction"); self.types("1")
        self.press("dpad_right"); self.types("2")
        self.press("dpad_right")
        self.press("plus")
        self.press("fraction"); self.types("3")
        self.press("dpad_right"); self.types("4")
        self.press("dpad_right")
        self.types("5")          # cursor now lives in the root slot
        self.assertIsNone(self.page.evaluate("() => { const p = getParent();"
                                           " return p ? p.slotName : '__none__'; }"),
                          "the cursor should be in the root slot")
        self.assertFalse(self.page.evaluate(
            "() => rootSlot.items.every(i => typeof i === 'string')"),
            "the root slot must hold templates for this to be the interesting case")
        st = self.state()
        self.assertEqual(st["cursor"], 1, "no cursor in the non-leaf slot")
        self.assertTrue(st["hasKatex"])
        self.assertIn("kx-cursor-slot", self.expr())
        # ...and it must not have been mistaken for a real slot.
        self.assertEqual(len(st["slotIds"]), 3,
                         f"only the four fraction parts are real slots: {st['slotIds']}")

    def test_nested_templates_still_serialize(self):
        self.press("fraction"); self.types("1")
        self.press("dpad_right"); self.types("2")
        self.assertIn("((1)/(2))", self.state()["expr"], self.state()["expr"])

    def test_del_still_edits_through_katex(self):
        self.press("integral")
        self.types("7")
        self.assertEqual(self.slot_items("body"), ["7"])
        self.press("del")
        self.assertEqual(self.slot_items("body"), [])
        self.assertTrue(self.state()["hasKatex"])

    def test_undo_still_restores_through_katex(self):
        self.press("integral")
        self.types("7")
        before = self.state()["expr"]
        self.page.evaluate("() => { popUndoState(); }")
        self.assertNotEqual(self.state()["expr"], before)
        self.assertTrue(self.state()["hasKatex"])


class TestOtherTemplatesAreKatex(ExprKatexBrowserCase):
    """KX-1 for the remaining skeletons."""

    def test_a_fraction_is_a_real_katex_fraction(self):
        self.press("fraction")
        html = self.expr()
        self.assertTrue(self.state()["hasKatex"])
        self.assertIn("mfrac", html, "the fraction is not a KaTeX \\frac")
        self.assertEqual(self.state()["slotIds"].__len__(), 2)

    def test_a_root_is_a_real_katex_root(self):
        self.press("sqrt")
        html = self.expr()
        self.assertTrue(self.state()["hasKatex"])
        self.assertTrue(re.search(r'class="[^"]*\bsqrt\b', html),
                        "the root is not a KaTeX radical")

    def test_the_derivative_is_a_real_katex_fraction(self):
        self.press("integral", shift=True)
        html = self.expr()
        self.assertTrue(self.state()["hasKatex"])
        self.assertIn("mfrac", html, "d/dx is not a KaTeX fraction")
        self.assertEqual(len(self.state()["slotIds"]), 2,
                         "the derivative should expose two slots")


if __name__ == "__main__":
    unittest.main()
