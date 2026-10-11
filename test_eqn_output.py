"""Item 6 regression coverage: EQN output rendering, S<->D and pagination.

Two layers:

* Static -- the EQN result must reach KaTeX through renderMath() and must no
  longer be assigned as a plain text blob; the pagination state and the
  S<->D toggle must exist and be wired to the D-pad.
* Browser -- the real rendered DOM is inspected for a KaTeX structure, a
  subscripted root, no stale solution after paginating, and a genuine stacked
  fraction when the exact form is selected. Loads frontend.html over file:// so
  no server is started. Skipped when Playwright or Chrome are unavailable.
"""
import pathlib
import re
import unittest

FRONTEND = (pathlib.Path(__file__).resolve().parent / "frontend.html").read_text(
    encoding="utf-8"
)

# Real roots captured from the engine (see the portable run in Item 5).
CUBIC = [{"real": 3, "imag": 0}, {"real": 2, "imag": 0}, {"real": 1.0000000000000002, "imag": 0}]
QUADRATIC_IRR = [{"real": -1.4142135623730951, "imag": 0}, {"real": 1.414213562373095, "imag": 0}]
QUARTIC = [1, 2, -2, -1]

try:
    from playwright.sync_api import sync_playwright

    _probe = sync_playwright().start()
    _browser = _probe.chromium.launch(channel="chrome")
    HAVE_BROWSER = True
    _browser.close()
    _probe.stop()
except Exception:  # pragma: no cover - environment dependent
    HAVE_BROWSER = False


class TestEqnRenderingWiring(unittest.TestCase):
    def test_result_is_typeset_by_katex(self):
        self.assertIn("function equationSolutionLatex(", FRONTEND)
        self.assertIn("renderMath(equationSolutionLatex(", FRONTEND)
        # The old blob assignment must be gone.
        self.assertNotIn("solution.textContent=formatEquationResult", FRONTEND)

    def test_host_is_attached_before_render_math(self):
        # renderMath resolves its target with getElementById, so a detached
        # host makes the KaTeX render a silent no-op.
        render = FRONTEND[FRONTEND.index("function renderEquationLCD()"):]
        render = render[: render.index("function updateScrollIndicators")]
        attach = render.index("view.appendChild(result);")
        paint = render.index("renderMath(equationSolutionLatex(")
        self.assertLess(attach, paint,
                        "the solution host must be in the document before typesetting")

    def test_pagination_state_and_navigation(self):
        self.assertIn("solutionIndex: 0", FRONTEND)
        result_phase = FRONTEND[FRONTEND.index("if (eq.phase === 'result') {"):]
        result_phase = result_phase[: result_phase.index("INEQUALITY MODE")]
        self.assertIn("eq.solutionIndex = (eq.solutionIndex + 1) % n", result_phase)
        self.assertIn("eq.solutionIndex = (eq.solutionIndex - 1 + n) % n", result_phase)
        self.assertIn("if (eq.solutionIndex >= n) eq.solutionIndex = n - 1", result_phase)

    def test_s_to_d_toggles_the_current_solution_form(self):
        result_phase = FRONTEND[FRONTEND.index("if (eq.phase === 'result') {"):]
        result_phase = result_phase[: result_phase.index("INEQUALITY MODE")]
        self.assertIn("rawKey === 's_to_d') { eq.exactForm = !eq.exactForm", result_phase)

    def test_only_simple_rationals_are_called_exact(self):
        # An irrational root has arbitrarily good rational approximations, so a
        # continued-fraction hit alone must not be reported as an exact value.
        fn = FRONTEND[FRONTEND.index("function equationNumberToLatex("):]
        fn = fn[: fn.index("function equationRootToLatex(")]
        self.assertIn("den <= 10000", fn)
        self.assertIn("Math.abs(num / den - snapped) < 1e-12", fn)

    def test_solver_rounding_noise_is_snapped(self):
        self.assertIn("Math.round(value)", FRONTEND[FRONTEND.index("function equationNumberToLatex("):])


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestEqnRenderedDOM(unittest.TestCase):
    URL = (pathlib.Path(__file__).resolve().parent / "frontend.html").as_uri()

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls._browser.new_page()
        cls.page.set_default_timeout(10000)
        cls.page.goto(cls.URL, wait_until="domcontentloaded")
        cls.page.wait_for_timeout(2500)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def _seed(self, roots, index=0, exact=False):
        self.page.evaluate(
            """([roots, index, exact]) => {
                 appState.mode = 'Equation/Func';
                 appState.equation = { selectedType: 'polynomial', phase: 'result',
                   numberOfEquations: 2, polynomialDegree: 2, currentEquation: 0,
                   currentCoefficient: 0, coefficientValues: [[1,-3,2]], inputBuffer: '',
                   selectedMenuItem: 0, resultState: roots, extremum: null,
                   solutionIndex: index, exactForm: exact };
                 appState.poweredOn = true; appState.splash = false;
                 renderLCD();
               }""",
            [roots, index, exact])
        self.page.wait_for_timeout(350)

    def _probe(self):
        return self.page.evaluate(
            """() => {
                 const host = document.getElementById('eqSolutionMath');
                 const body = document.getElementById('lcdEquationBody');
                 const html = host && host.querySelector('.katex-html');
                 return {
                   katex: body ? body.querySelectorAll('.katex').length : 0,
                   sub: host ? host.querySelectorAll('.msub,.msupsub').length : 0,
                   frac: host ? host.querySelectorAll('.mfrac').length : 0,
                   text: html ? html.textContent : (host ? host.textContent : ''),
                   pos: (body && body.querySelector('.eq-solution-pos'))
                          ? body.querySelector('.eq-solution-pos').textContent : null,
                 };
               }""")

    def _press(self, key):
        self.page.evaluate(
            """(key) => { appState.shift = false; appState.alpha = false;
                 handleKey({ dataset: { key: key }, classList: { toggle: () => {} },
                             hasAttribute: () => false, getAttribute: () => null });
                 renderLCD(); }""",
            key)
        self.page.wait_for_timeout(250)

    def test_solution_is_rendered_by_katex_with_a_real_subscript(self):
        self._seed(QUADRATIC_IRR)
        d = self._probe()
        self.assertGreaterEqual(d["katex"], 1, "no KaTeX node in the EQN result")
        self.assertGreaterEqual(d["sub"], 1, "root index is not a KaTeX subscript")
        self.assertNotIn("$", d["text"])
        self.assertIn("1/2", d["pos"])

    def test_pagination_shows_each_root_once_and_wraps(self):
        self._seed(QUADRATIC_IRR)
        first = self._probe()["text"]
        self._press("dpad_down")
        second = self._probe()
        self.assertNotEqual(first, second["text"], "D-pad did not change the solution")
        self.assertIn("2/2", second["pos"])
        self.assertEqual(second["katex"], 1, "duplicate KaTeX nodes accumulated")
        self._press("dpad_down")
        self.assertIn("1/2", self._probe()["pos"], "did not wrap past the last solution")
        self._press("dpad_up")
        self.assertIn("2/2", self._probe()["pos"], "did not wrap backwards")

    def test_all_four_quartic_roots_are_reachable(self):
        self._seed(QUARTIC)
        seen = []
        for _ in range(4):
            seen.append(self._probe()["text"])
            self._press("dpad_down")
        self.assertEqual(len(set(seen)), 4, seen)

    def test_s_to_d_switches_decimal_for_exact_fraction(self):
        self._seed([{"real": 0.5, "imag": 0}, {"real": 2, "imag": 0}])
        decimal = self._probe()
        self.assertEqual(decimal["frac"], 0)
        self.assertIn("0.5", decimal["text"])
        self._press("s_to_d")
        exact = self._probe()
        self.assertEqual(exact["frac"], 1, "exact form is not a real KaTeX fraction")
        self.assertNotIn("0.5", exact["text"])
        self._press("s_to_d")
        self.assertIn("0.5", self._probe()["text"], "S<->D did not toggle back")

    def test_irrational_root_has_no_fake_exact_form(self):
        self._seed(QUADRATIC_IRR, exact=True)
        d = self._probe()
        self.assertEqual(d["frac"], 0, "an irrational root was turned into a fraction")
        self.assertIn("1.41", d["text"])
        self.assertIn("a b/c", d["pos"])


if __name__ == "__main__":
    unittest.main()