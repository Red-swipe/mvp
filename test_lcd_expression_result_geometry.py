"""Item 1 regression coverage: the LCD expression region and the result region
must occupy distinct space and must not collide.

The layout contract, measured on the real build:
  .lcd            103px tall, overflow:hidden
  .lcd-status-bar  12px, in flow, at the top
  .lcd-expr-viewport 58px, in flow, directly under the status bar
  .lcd-result-line   absolutely positioned, bottom-right, out of flow

Because the result line is absolutely positioned, comparing its BOX against the
expression viewport's BOX is meaningless -- the boxes legitimately overlap
vertically while the visible text does not. So every assertion here is made on
real rendered geometry:

  * the visible expression ink (text rects clipped by the scrolling viewport)
  * the visible result ink
  * the intersection of those two rectangles

Test geometry caught a real defect: KaTeX draws a stacked fraction as a vlist
~37px tall while `line-height:1` keeps its line box ~20px, so the ink spilled
9px below the box. At `bottom:2px` an exact result such as 5/8 had its
denominator clipped by `.lcd`'s overflow:hidden. test_result_ink_stays_inside
_the_lcd is the test that fails against that.
"""
import json
import pathlib
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

FRONTEND_PATH = pathlib.Path(__file__).resolve().parent / "frontend.html"

try:
    from playwright.sync_api import sync_playwright

    _pw = sync_playwright().start()
    _b = _pw.chromium.launch(channel="chrome")
    HAVE_BROWSER = True
    _b.close()
    _pw.stop()
except Exception:  # pragma: no cover - environment dependent
    HAVE_BROWSER = False

# Measured on the real build: the expression viewport is a fixed 58px band and
# the result line is anchored to the bottom-right of a 103px LCD.
EXPR_BAND_PX = 58
STATUS_BAR_PX = 12
TOL = 1.0          # sub-pixel slack; never widened to mask a real collision


MEASURE = """() => {
  const r = (el) => { if(!el) return null; const b = el.getBoundingClientRect();
    return {top:+b.top.toFixed(2), bottom:+b.bottom.toFixed(2),
            left:+b.left.toFixed(2), right:+b.right.toFixed(2),
            w:+b.width.toFixed(2), h:+b.height.toFixed(2)}; };
  const inkOf = (el) => { if(!el) return null;
    const rects = [];
    const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let n; while ((n = walk.nextNode())) {
      if (!n.nodeValue.trim()) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const x of rg.getClientRects())
        if (x.height > 0 && x.width > 0) rects.push(x);
    }
    if (!rects.length) return null;
    const top = Math.min(...rects.map(x=>x.top)), bot = Math.max(...rects.map(x=>x.bottom));
    const lft = Math.min(...rects.map(x=>x.left)), rgt = Math.max(...rects.map(x=>x.right));
    return {top:+top.toFixed(2), bottom:+bot.toFixed(2), left:+lft.toFixed(2),
            right:+rgt.toFixed(2), h:+(bot-top).toFixed(2)}; };
  const clip = (a, b) => { if(!a||!b) return null;
    const top = Math.max(a.top,b.top), bot = Math.min(a.bottom,b.bottom);
    const lft = Math.max(a.left,b.left), rgt = Math.min(a.right,b.right);
    if (bot <= top || rgt <= lft) return null;
    return {top:+top.toFixed(2), bottom:+bot.toFixed(2),
            left:+lft.toFixed(2), right:+rgt.toFixed(2)}; };
  const vp  = document.getElementById('lcdExprViewport');
  const ec  = document.getElementById('lcdExprContent');
  const rl  = document.getElementById('lcdResultLine');
  const lcd = document.getElementById('lcdDisplay');
  const vpBox = vp ? r(vp) : null;
  const resBox = rl ? r(rl) : null;
  const exprInk = inkOf(ec), resInk = inkOf(rl);
  const visExpr = clip(exprInk, vpBox);
  const visRes  = resInk ? clip(resInk, lcd ? r(lcd) : null) : null;
  const lcdBox = r(lcd);
  return { lcd: lcdBox, calc: r(document.getElementById('lcdCalc')),
           status: r(document.querySelector('.lcd-status-bar')),
           viewport: vpBox, content: r(ec), result: resBox,
           visibleExprInk: visExpr, resultInk: resInk,
           viewportScroll: vp ? {sh: vp.scrollHeight, ch: vp.clientHeight,
                                 st: vp.scrollTop, sl: vp.scrollLeft} : null,
           resultText: rl ? rl.textContent : null,
           ioMode: appState.settings ? appState.settings.inputOutput : null };
}"""


def intersects(a, b):
    """True when two rectangles share area. Either axis separating is enough."""
    if not a or not b:
        return False
    return not (a["bottom"] <= b["top"] or b["bottom"] <= a["top"]
                or a["right"] <= b["left"] or b["right"] <= a["left"])


class TestResultLineCss(unittest.TestCase):
    FRONTEND = FRONTEND_PATH.read_text(encoding="utf-8")

    @staticmethod
    def _strip_css_comments(text):
        out, i, n = [], 0, len(text)
        while i < n:
            if text.startswith("/*", i):
                end = text.find("*/", i + 2)
                i = n if end == -1 else end + 2
            else:
                out.append(text[i])
                i += 1
        return "".join(out)

    def _rule(self, selector):
        css = self._strip_css_comments(self.FRONTEND)
        start = css.index(f"{selector}{{")
        return css[start: css.index("}", start)]

    def test_result_line_is_anchored_low_enough_for_tall_ink(self):
        # Comments are stripped first: the rule carries a comment explaining
        # the measured reason for the value, and quoting the old value there
        # must not be mistaken for the declaration still using it.
        rule = self._rule(".lcd-result-line")
        self.assertIn("bottom:8px", rule)
        self.assertNotIn("bottom:2px", rule)

    def test_result_line_stays_bottom_right(self):
        rule = self._rule(".lcd-result-line")
        self.assertIn("position:absolute", rule)
        self.assertIn("right:4px", rule)


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestLcdGeometry(unittest.TestCase):
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

    def open_at(self, size=(520, 1000)):
        page = self.browser.new_page(viewport={"width": size[0], "height": size[1]})
        page.goto(f"http://127.0.0.1:{self.port}/", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        return page

    def calc(self, page, expr, io="LineI/LineO"):
        page.evaluate(
            """([e,io]) => { appState.settings.inputOutput = io; renderLCD();
                 resetExpr(); appState.result = null; appState.resultDisplayed = false;
                 for (const c of e) insertToken(c); evaluate(); }""",
            [expr, io])
        page.wait_for_function("()=>appState.resultDisplayed||appState.error", timeout=15000)
        page.wait_for_timeout(450)
        return page.evaluate(MEASURE)

    # -- the two regions ---------------------------------------------------
    def test_expression_band_sits_directly_under_the_status_bar(self):
        page = self.open_at()
        try:
            m = self.calc(page, "7*8")
            self.assertAlmostEqual(m["status"]["h"], STATUS_BAR_PX, delta=TOL)
            self.assertAlmostEqual(m["status"]["bottom"], m["viewport"]["top"], delta=TOL,
                                   msg="expression band does not start under the status bar")
            self.assertAlmostEqual(m["viewport"]["h"], EXPR_BAND_PX, delta=TOL,
                                   msg="expression band changed height")
        finally:
            page.close()

    def test_expression_and_result_occupy_distinct_regions(self):
        # Not a box-vs-box comparison: the result box is absolutely positioned
        # and legitimately overlaps the viewport box. The visible INK must not.
        for io in ("LineI/LineO", "DecimalO", "MathI/MathO"):
            with self.subTest(io=io):
                page = self.open_at()
                try:
                    m = self.calc(page, "7*8", io=io)
                    self.assertIsNotNone(m["visibleExprInk"], "expression ink not found")
                    self.assertIsNotNone(m["resultInk"], "result ink not found")
                    self.assertFalse(
                        intersects(m["visibleExprInk"], m["resultInk"]),
                        "visible expression and result overlap: "
                        f"{m['visibleExprInk']} vs {m['resultInk']}")
                finally:
                    page.close()

    def test_result_stays_below_the_status_bar(self):
        page = self.open_at()
        try:
            m = self.calc(page, "7*8")
            self.assertGreater(m["resultInk"]["top"], m["status"]["bottom"],
                               "result rose into the status bar")
        finally:
            page.close()

    # -- the defect this suite was written for ----------------------------
    def test_result_ink_stays_inside_the_lcd(self):
        # KaTeX draws a stacked \frac ~37px tall against a ~20px line box, so
        # its ink spills below the box. At bottom:2px that reached y=367.17 in
        # a 103px LCD ending at y=365 and overflow:hidden ate the denominator.
        for expr in ("5/8", "7/3", "1/4"):
            with self.subTest(expr=expr):
                page = self.open_at()
                try:
                    m = self.calc(page, expr, io="MathI/MathO")
                    self.assertIsNotNone(m["resultInk"])
                    self.assertLessEqual(
                        m["resultInk"]["bottom"], m["lcd"]["bottom"] + TOL,
                        "result ink is clipped by the LCD: "
                        f"ink bottom {m['resultInk']['bottom']} > lcd bottom {m['lcd']['bottom']}")
                    self.assertGreaterEqual(m["resultInk"]["top"], m["lcd"]["top"] - TOL)
                    self.assertLessEqual(m["resultInk"]["right"], m["lcd"]["right"] + TOL)
                finally:
                    page.close()

    def test_result_box_stays_inside_the_lcd(self):
        page = self.open_at()
        try:
            m = self.calc(page, "5/8", io="MathI/MathO")
            self.assertLessEqual(m["result"]["bottom"], m["lcd"]["bottom"] + TOL)
            self.assertLessEqual(m["result"]["right"], m["lcd"]["right"] + TOL)
            self.assertGreaterEqual(m["result"]["top"], m["lcd"]["top"] - TOL)
        finally:
            page.close()

    # -- long / scrolling expressions -------------------------------------
    def test_long_expression_does_not_move_or_overlap_the_result(self):
        long_expr = "1+2+3+4+5+6+7+8+9+10+11+12+13+14+15+16+17+18+19+20"
        page = self.open_at()
        try:
            short = self.calc(page, "7*8")
            page.evaluate("(c)=>{ for (const k of c) insertToken(k); evaluate(); }",
                          long_expr[3:])
            page.wait_for_function("()=>appState.resultDisplayed||appState.error",
                                   timeout=15000)
            page.wait_for_timeout(500)
            long_m = page.evaluate(MEASURE)

            # a long expression scrolls horizontally; it must not push the
            # result down, out of the LCD, or into the expression ink
            self.assertGreater(long_m["viewportScroll"]["sl"], 0,
                               "long expression did not scroll (test is not exercising it)")
            self.assertAlmostEqual(long_m["resultInk"]["bottom"],
                                   short["resultInk"]["bottom"], delta=TOL,
                                   msg="long expression moved the result line")
            self.assertLessEqual(long_m["resultInk"]["bottom"],
                                 long_m["lcd"]["bottom"] + TOL)
            self.assertFalse(intersects(long_m["visibleExprInk"], long_m["resultInk"]),
                             "long expression overlaps the result")
            # the expression scrolls, it is never vertically clipped
            self.assertLessEqual(long_m["viewportScroll"]["sh"],
                                 long_m["viewportScroll"]["ch"] + TOL)
        finally:
            page.close()

    def test_tall_katex_vlist_does_not_collide_with_a_fraction_result(self):
        # Sigma is the tallest expression ink (~57px, reaching y=335.86); an
        # exact fraction is the tallest result ink (~37px). Force both at once.
        for bottom_case in ("existing",):
            with self.subTest(bottom_case):
                page = self.open_at()
                try:
                    page.evaluate(
                        """() => { appState.settings.inputOutput='MathI/MathO';
                             appState.settings.fractionResult='d/c';
                             resetExpr(); renderLCD(); }""")
                    page.evaluate(
                        """() => { const x=document.querySelector('[data-key="variable"]');
                             appState.shift = true; handleKey(x);
                             appState.shift = false; renderLCD(); }""")
                    page.wait_for_timeout(400)
                    for c in "123":
                        page.evaluate("(c)=>insertToken(c)", c)
                        page.wait_for_timeout(130)
                    page.evaluate(
                        """() => { appState.result='5/8'; appState.resultDisplayed=true;
                             appState.isFractionMode=true; renderLCD(); }""")
                    page.wait_for_timeout(700)
                    m = page.evaluate(MEASURE)
                    self.assertIsNotNone(m["visibleExprInk"])
                    self.assertIsNotNone(m["resultInk"])
                    self.assertFalse(
                        intersects(m["visibleExprInk"], m["resultInk"]),
                        "tall Sigma vlist collides with a fraction result: "
                        f"{m['visibleExprInk']} vs {m['resultInk']}")
                    self.assertLessEqual(m["resultInk"]["bottom"],
                                         m["lcd"]["bottom"] + TOL)
                finally:
                    page.close()

    def test_geometry_is_stable_across_viewports(self):
        for size in ((520, 1000), (1000, 1300)):
            with self.subTest(viewport=size):
                page = self.open_at(size)
                try:
                    m = self.calc(page, "5/8", io="MathI/MathO")
                    self.assertAlmostEqual(m["viewport"]["h"], EXPR_BAND_PX, delta=TOL)
                    self.assertFalse(intersects(m["visibleExprInk"], m["resultInk"]))
                    self.assertLessEqual(m["resultInk"]["bottom"],
                                         m["lcd"]["bottom"] + TOL)
                finally:
                    page.close()

    def test_empty_result_does_not_break_the_measurement(self):
        page = self.open_at()
        try:
            page.evaluate("()=>{resetExpr(); appState.result=null; renderLCD();}")
            page.wait_for_timeout(300)
            m = page.evaluate(MEASURE)
            self.assertIsNone(m["resultInk"])
            self.assertFalse(intersects(m["visibleExprInk"], m["resultInk"]))
        finally:
            page.close()