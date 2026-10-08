"""Item 9 regression coverage: MathI/MathO exact output, S<->D, and the
DecimalO / LineI-LineO output modes.

Defect this locks down: `input_output` was stored in setup but never used to
format a result, and the engine only ever returns a decimal. So MathI/MathO
showed 2.5 for 5/2 instead of the exact fraction, and the I/O mode had no effect
on output at all. A second bug followed: S<->D's isFractionMode flag was left
stale from a previous calculation, so after switching to DecimalO/LineO the
first S<->D press could be a no-op.

Static layer: the exact-output helper exists and is wired into storeCalcAnswer.
Browser layer: the real rendered DOM for every mode, driven through evaluate()
and the S<->D key. Loads frontend.html over file:// -- no server.
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


class TestExactOutputWiring(unittest.TestCase):
    def test_helper_exists_and_is_used(self):
        self.assertIn("function exactFractionResult(", FRONTEND)
        store = FRONTEND[FRONTEND.index("function storeCalcAnswer("):]
        store = store[: store.index("async function evaluate()")]
        self.assertIn("exactFractionResult(", store)

    def test_only_mathto_produces_exact_output(self):
        store = FRONTEND[FRONTEND.index("function storeCalcAnswer("):]
        store = store[: store.index("async function evaluate()")]
        self.assertIn("ioMode === 'MathI/MathO'", store)
        self.assertIn("appState.settings.inputOutput", store)

    def test_settings_are_read_defensively(self):
        # storeCalcAnswer is driven by harnesses whose appState stub has no
        # settings object, so the read must not throw.
        store = FRONTEND[FRONTEND.index("function storeCalcAnswer("):]
        store = store[: store.index("async function evaluate()")]
        self.assertNotIn("appState.settings.inputOutput ===", store)
        self.assertIn("appState.settings ?", store)

    def test_fraction_flag_is_refreshed_for_scalars(self):
        store = FRONTEND[FRONTEND.index("function storeCalcAnswer("):]
        store = store[: store.index("async function evaluate()")]
        self.assertIn("appState.isFractionMode = scalar.includes('/')", store)

    def test_irrational_decimal_is_not_faked_into_a_fraction(self):
        fn = FRONTEND[FRONTEND.index("function exactFractionResult("):]
        fn = fn[: fn.index("function storeCalcAnswer(")]
        self.assertIn("den > 10000", fn)          # 1/3 has no short exact form
        self.assertIn("Math.abs(num / den - n) > 1e-12", fn)


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestOutputModes(unittest.TestCase):
    URL = FRONTEND_PATH.as_uri()

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls._browser.new_page(viewport={"width": 1000, "height": 1300})
        cls.page.set_default_timeout(10000)
        cls.page.goto(cls.URL, wait_until="domcontentloaded")
        cls.page.wait_for_timeout(2500)
        cls.page.evaluate("() => { appState.poweredOn = true; appState.splash = false; renderLCD(); }")
        cls.page.wait_for_timeout(300)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    # This KaTeX build renders .mfrac as ONE vlist of absolutely positioned
    # children (no .num/.den classes): numerator, frac-line, denominator, each
    # with its own negative `top`. Most negative top == numerator.
    PROBE = """
    () => {
      const host = document.getElementById('lcdResultLine');
      const html = host ? host.querySelector('.katex-html') : null;
      const frac = host ? host.querySelector('.mfrac') : null;
      let num = null, den = null;
      if (frac) {
        const blocks = Array.from(frac.querySelectorAll('.vlist > span[style*="top"]'))
          .map(el => ({ top: parseFloat((el.style.top || '0em').replace('em','')) || 0,
                        txt: (el.textContent || '').trim() })).filter(t => t.txt);
        blocks.sort((a, b) => a.top - b.top);
        if (blocks.length) { num = blocks[0].txt; den = blocks[blocks.length-1].txt; }
      }
      return { result: appState.result,
               text: html ? html.textContent.replace(/\\u200b/g,'') : (host ? host.textContent : ''),
               frac: !!frac, num, den,
               isFractionMode: appState.isFractionMode,
               katex: host ? host.querySelectorAll('.katex').length : 0 };
    }"""

    def _mode(self, io_mode, frac_result=None):
        self.page.evaluate(
            """(o) => { appState.settings.inputOutput = o.io;
                 if (o.frac) appState.settings.fractionResult = o.frac;
                 renderLCD(); }""",
            {"io": io_mode, "frac": frac_result})
        self.page.wait_for_timeout(150)

    def _calc(self, expr):
        self.page.evaluate(
            """(e) => { resetExpr(); for (const c of e) insertToken(c); evaluate(); }""", expr)
        self.page.wait_for_timeout(300)
        return self.page.evaluate(self.PROBE)

    def _sd(self):
        self.page.evaluate("() => { toggleAnswerFormat(false); }")
        self.page.wait_for_timeout(300)
        return self.page.evaluate(self.PROBE)

    # ── MathI/MathO ─────────────────────────────────────────────────────────
    def test_mathto_renders_a_real_stacked_fraction(self):
        self._mode("MathI/MathO", "d/c")
        d = self._calc("5/2")
        self.assertTrue(d["frac"], "5/2 is not a KaTeX fraction")
        self.assertGreaterEqual(d["katex"], 1)
        self.assertEqual((d["num"], d["den"]), ("5", "2"))
        self.assertEqual(d["result"], "5/2")
        self.assertNotIn("\\frac", d["text"])
        self.assertNotIn("$", d["text"])

    def test_mathto_quarter_is_exact(self):
        self._mode("MathI/MathO", "d/c")
        d = self._calc("1/4")
        self.assertTrue(d["frac"])
        self.assertEqual((d["num"], d["den"]), ("1", "4"))

    def test_abc_setting_yields_a_mixed_number(self):
        self._mode("MathI/MathO", "ab/c")
        d = self._calc("5/2")
        self.assertEqual(d["result"], "2 1/2")
        self.assertTrue(d["frac"])
        self.assertEqual((d["num"], d["den"]), ("1", "2"))

    def test_repeating_decimal_is_not_faked_into_a_fraction(self):
        self._mode("MathI/MathO", "d/c")
        d = self._calc("1/3")
        self.assertFalse(d["frac"])
        self.assertNotIn("/", str(d["result"]))

    # ── S<->D ───────────────────────────────────────────────────────────────
    def test_sd_round_trip(self):
        self._mode("MathI/MathO", "d/c")
        self._calc("5/2")
        a = self._sd()
        self.assertFalse(a["frac"])
        self.assertIn("2.5", a["text"])
        c = self._sd()
        self.assertTrue(c["frac"])
        self.assertEqual((c["num"], c["den"]), ("5", "2"))

    def test_sd_quarter(self):
        self._mode("MathI/MathO", "d/c")
        self._calc("1/4")
        self.assertIn("0.25", self._sd()["text"])

    # ── DecimalO / LineO ────────────────────────────────────────────────────
    def test_decimalo_never_stacks(self):
        self._mode("MathI/DecimalO")
        for expr, want in (("5/2", "2.5"), ("1/4", "0.25")):
            with self.subTest(expr=expr):
                d = self._calc(expr)
                self.assertFalse(d["frac"])
                self.assertIn(want, d["text"])

    def test_lineio_never_stacks(self):
        self._mode("LineI/LineO")
        for expr, want in (("5/2", "2.5"), ("1/4", "0.25")):
            with self.subTest(expr=expr):
                d = self._calc(expr)
                self.assertFalse(d["frac"])
                self.assertIn(want, d["text"])

    # ── setup synchronisation ───────────────────────────────────────────────
    def test_setup_change_takes_effect_on_the_next_calculation(self):
        self._mode("MathI/MathO", "d/c")
        self.assertTrue(self._calc("5/2")["frac"])
        self._mode("LineI/LineO")
        self.assertFalse(self._calc("5/2")["frac"])
        self._mode("MathI/DecimalO")
        self.assertFalse(self._calc("5/2")["frac"])
        self._mode("MathI/MathO", "d/c")
        self.assertTrue(self._calc("5/2")["frac"])

    def test_sd_flag_is_not_stale_after_switching_mode(self):
        # A fraction in MathO, then switch to DecimalO: the first S<->D must not
        # be swallowed because isFractionMode was left over as True.
        self._mode("MathI/MathO", "d/c")
        self._calc("5/2")
        self.assertTrue(self.page.evaluate("() => appState.isFractionMode"))
        self._mode("MathI/DecimalO")
        self._calc("5/2")
        self.assertFalse(self.page.evaluate("() => appState.isFractionMode"))
        self._mode("MathI/MathO", "d/c")
        self.assertTrue(self._calc("5/2")["frac"])


if __name__ == "__main__":
    unittest.main()