"""Item 7 regression coverage: the sigma template's limits must not be clipped.

Root cause this locks down: the expression line is typeset by KaTeX in DISPLAY
mode so the sigma gets its ClassWiz arrangement (limits stacked above and below
the operator). That vlist is ~50.8px tall, and `.lcd-expr-viewport` used to be
50px tall with `overflow-y:hidden`, so the bottom of the vlist -- the LOWER
LIMIT -- was cut off.

Static layer: the viewport must be tall enough to hold a display-mode sum while
still leaving Item 1's result band clear.
Browser layer: real bounding boxes, plus the Item 1 invariant that the expression
stays above the result line. Loads frontend.html over file:// -- no server.
"""
import pathlib
import re
import unittest

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

# Status bar (12px) + expression viewport must stay clear of the result band,
# which begins at LCD height 103 - bottom 2 - result line 20 = 81px.
STATUS_BAR_H = 12
RESULT_BAND_TOP = 81


def _viewport_rule():
    """The .lcd-expr-viewport declaration with CSS comments stripped.

    The rule's own comment quotes `\\sum_{i=1}^{3}`, whose braces would otherwise
    terminate the naive `[^}]*` match early.
    """
    m = re.search(r"\.lcd-expr-viewport\s*\{", FRONTEND)
    assert m, "no .lcd-expr-viewport rule"
    start = m.end()
    depth = 1
    i = start
    while i < len(FRONTEND) and depth:
        if FRONTEND[i] == "{":
            depth += 1
        elif FRONTEND[i] == "}":
            depth -= 1
        i += 1
    body = FRONTEND[start : i - 1]
    return re.sub(r"/\*.*?\*/", "", body, flags=re.S)


def _viewport_height():
    h = re.search(r"height:\s*(\d+)px", _viewport_rule())
    assert h, "no explicit height on .lcd-expr-viewport"
    return int(h.group(1))


class TestSigmaLayoutCSS(unittest.TestCase):
    def test_viewport_is_tall_enough_for_a_display_mode_sum(self):
        # Measured: the \sum_{}^{} vlist is 50.8px tall and sits 3px below the
        # viewport top, so it needs >53.8px before overflow-y clips it.
        self.assertGreaterEqual(_viewport_height(), 58)

    def test_viewport_still_clips_overflow(self):
        self.assertIn("overflow-y:hidden", _viewport_rule())

    def test_expression_region_does_not_collide_with_the_result(self):
        self.assertLess(STATUS_BAR_H + _viewport_height(), RESULT_BAND_TOP)

    def test_sigma_latex_keeps_both_limits(self):
        # The sigma LaTeX is correct; only the container was too short. Guard
        # against a "fix" that rewrites the serialisation instead.
        self.assertRegex(FRONTEND, r"case 'sigma': return '\\\\sum_\{")


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestSigmaRenderedGeometry(unittest.TestCase):
    URL = FRONTEND_PATH.as_uri()

    # (label, body items, lower items, upper items, expected serialized expression)
    CASES = [
        ("sum 1..3 of x^2", ["x", "^", "2"], ["1"], ["3"], "sigma(x^2,1,3)"),
        ("sum 1..3 of x", ["x"], ["1"], ["3"], "sigma(x,1,3)"),
        ("sum 1..12 of x", ["x"], ["1"], ["1", "2"], "sigma(x,1,12)"),
        ("sum 10..99 of x", ["x"], ["1", "0"], ["9", "9"], "sigma(x,10,99)"),
    ]

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls._browser.new_page(viewport={"width": 900, "height": 1200})
        cls.page.set_default_timeout(10000)
        cls.page.goto(cls.URL, wait_until="domcontentloaded")
        cls.page.wait_for_timeout(2500)
        cls.page.evaluate(
            "() => { appState.poweredOn = true; appState.splash = false; renderLCD(); }"
        )
        cls.page.wait_for_timeout(300)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def _render(self, body, lower, upper):
        self.page.evaluate(
            """([body, lower, upper]) => {
                 resetExpr(); insertSigma();
                 const t = rootSlot.items[0];
                 t.body.items = body; t.lower.items = lower; t.upper.items = upper;
                 renderLCD();
               }""",
            [body, lower, upper])
        self.page.wait_for_timeout(350)
        return self.page.evaluate(
            """() => {
                 const vp = document.getElementById('lcdExprViewport');
                 const cont = document.getElementById('lcdExprContent');
                 const res = document.getElementById('lcdResultLine');
                 const html = cont.querySelector('.katex-html');
                 const kx = cont.querySelector('.katex');
                 const op = html ? html.querySelector('.mop') : null;
                 // This KaTeX version stacks both limits in one .vlist-t.
                 const vl = html ? html.querySelector('.vlist-t') : null;
                 const bb = e => { if (!e) return null; const r = e.getBoundingClientRect();
                   return { top:r.top, bottom:r.bottom }; };
                 return {
                   vp: bb(vp), katex: bb(kx), cont: bb(cont), res: bb(res),
                   vlist: vl ? vl.textContent.replace(/[^0-9a-zA-Z]/g, '') : '',
                   body: (function(){ if (!html) return '';
                     const c = html.cloneNode(true);
                     c.querySelectorAll('.vlist-t,.mop').forEach(n => n.remove());
                     return c.textContent.replace(/[^0-9a-zA-Z^=]/g,''); })(),
                   opLimits: !!(op && op.classList.contains('op-limits')),
                   expr: (typeof getExpr === 'function') ? getExpr() : null,
                 };
               }""")

    def test_limits_are_present_and_not_clipped(self):
        for label, body, lower, upper, expr in self.CASES:
            with self.subTest(case=label):
                d = self._render(body, lower, upper)
                self.assertEqual(d["expr"], expr)
                self.assertTrue(d["opLimits"], "sigma is not an op-limits structure")
                lower_s = "".join(lower)
                upper_s = "".join(upper)
                self.assertIn(lower_s, d["vlist"], f"lower limit {lower_s!r} missing")
                self.assertIn(upper_s, d["vlist"], f"upper limit {upper_s!r} missing")
                self.assertTrue(d["body"], "sigma body missing")
                # Negative slack == the KaTeX box pokes outside an
                # overflow:hidden viewport, i.e. the lower limit is cut off.
                self.assertGreaterEqual(
                    d["katex"]["top"] - d["vp"]["top"], 0,
                    f"{label}: expression clipped at the top")
                self.assertGreaterEqual(
                    d["vp"]["bottom"] - d["katex"]["bottom"], 0,
                    f"{label}: sigma lower limit clipped at the bottom")

    def test_expression_stays_above_the_result(self):
        for label, body, lower, upper, _ in self.CASES:
            with self.subTest(case=label):
                d = self._render(body, lower, upper)
                self.assertLess(
                    d["cont"]["bottom"], d["res"]["top"],
                    f"{label}: expression overlaps the result line (Item 1)")


if __name__ == "__main__":
    unittest.main()
