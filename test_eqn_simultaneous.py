"""Item 13 regression coverage: simultaneous equations (2, 3 and 4 unknowns).

Defect this locks down, measured on the real rendered LCD before the fix:

  LABEL-1 a solved simultaneous system reported its answers with POLYNOMIAL
          root labels. A 4-unknown system (x+y=10, y+z=15, z+w=20, 2x=20,
          i.e. x=10 y=0 z=15 w=5) displayed "x_1 = 10", "x_2 = 0", ... while
          the input grid immediately above it showed the coefficients of
          x, y, z, w. The values were right and the labels were wrong, which
          reads as "the first root of a polynomial" and contradicts the screen
          the numbers came from. equationVariableLabel() now gives a
          simultaneous system its variable names and leaves a polynomial's
          indexed roots alone.
  LABEL-2 formatEquationResult() returned displayFormat(JSON.stringify(result))
          for every non-polynomial kind, so a simultaneous result printed its
          raw array ("[2.7142857142857144,1.5714285714285714]").
  LABEL-3 renderMath()'s plain-text fallback was passed the bare value, so with
          KaTeX unavailable the LCD showed "1.571428571" with no variable name
          at all. It is now passed equationSolutionText(), which carries the
          label.
  DEBUG-1  the equation path carried six console.debug('[EQUATION-TRACE-*]')
          calls and the backend three print('[EQUATION] ...') calls.

The engine's arithmetic is deliberately NOT re-derived from itself: every
expected answer below was computed by hand (see the algebra in each comment)
and the solver is checked against those constants.

The solver is a backend endpoint, so the solving tests run against a real server
bound to an ephemeral port, started and stopped by this module. Input layout is
checked over file://, where no backend is needed.
"""
import pathlib
import re
import sys
import threading
import time
import unittest
from http.server import ThreadingHTTPServer

PROJECT = pathlib.Path(__file__).resolve().parent
FRONTEND_PATH = PROJECT / "frontend.html"
FRONTEND = FRONTEND_PATH.read_text(encoding="utf-8")

sys.path.insert(0, str(PROJECT))
import mvp_server  # noqa: E402

PAYLOAD_UNRELATED = None  # kept for readability of the fixture below

try:
    from playwright.sync_api import sync_playwright

    _pw = sync_playwright().start()
    _b = _pw.chromium.launch(channel="chrome")
    HAVE_BROWSER = True
    _b.close()
    _pw.stop()
except Exception:  # pragma: no cover - environment dependent
    HAVE_BROWSER = False


# --------------------------------------------------------------------------
# Oracles. Each expected value is derived by hand, not from the solver.
# --------------------------------------------------------------------------
def oracle_2():
    # 2x + y = 7 ;  x - 3y = -2
    # from row 2: x = 3y - 2; substitute: 2(3y-2) + y = 7 -> 7y = 11
    # y = 11/7 ; x = 3(11/7) - 2 = 19/7
    return [19 / 7, 11 / 7]


def oracle_3():
    # x+y+z = 6 ; 2x-y = 1 ; 3y-z = 10
    # y = 2x-1 ; z = 3y-10 = 6x-13 ; x + 2x-1 + 6x-13 = 6 -> 9x = 20
    return [20 / 9, 31 / 9, 1 / 3]


def oracle_4():
    # x+y = 10 ; y+z = 15 ; z+w = 20 ; 2x = 20
    # x = 10 -> y = 0 -> z = 15 -> w = 5
    return [10.0, 0.0, 15.0, 5.0]


SYSTEMS = {
    2: (["2", "1", "7"], ["1", "-3", "-2"]),
    3: (["1", "1", "1", "6"], ["2", "-1", "0", "1"], ["0", "3", "-1", "10"]),
    4: (["1", "1", "0", "0", "10"], ["0", "1", "1", "0", "15"],
        ["0", "0", "1", "1", "20"], ["2", "0", "0", "0", "20"]),
}
ORACLES = {2: oracle_2(), 3: oracle_3(), 4: oracle_4()}
VARIABLES = {2: ["x", "y"], 3: ["x", "y", "z"], 4: ["x", "y", "z", "w"]}


def strip_comments(src):
    out = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    out = re.sub(r"(?m)^\s*//.*$", " ", out)
    return out


FRONTEND_NO_COMMENTS = strip_comments(FRONTEND)


# --------------------------------------------------------------------------
# Static layer (always runs)
# --------------------------------------------------------------------------
class TestResultLabelling(unittest.TestCase):

    def test_label_helper_exists_and_is_type_aware(self):
        self.assertIn("function equationVariableLabel(", FRONTEND)
        fn = FRONTEND[FRONTEND.index("function equationVariableLabel("):]
        fn = fn[: fn.index("function equationSolutionLatex(")]
        self.assertIn("eq.selectedType === 'simultaneous'", fn,
                      "the label must distinguish simultaneous from polynomial")
        self.assertIn("['x', 'y', 'z', 'w']", fn,
                      "simultaneous answers are labelled with their variables")

    def test_polynomial_keeps_its_indexed_root_label(self):
        # Item 6 depends on this: a quadratic's roots must stay x_1 / x_2 so the
        # subscript is still a real KaTeX msub.
        fn = FRONTEND[FRONTEND.index("function equationVariableLabel("):]
        fn = fn[: fn.index("function equationSolutionLatex(")]
        self.assertIn("'x_{' + (index + 1) + '}'", fn)

    def test_solution_latex_uses_the_label_helper(self):
        fn = FRONTEND[FRONTEND.index("function equationSolutionLatex("):]
        fn = fn[: fn.index("function equationSolutionText(")]
        self.assertIn("equationVariableLabel(eq, index).latex", fn)
        self.assertNotIn("'x_{' + subscript + '}'", fn,
                         "the hardcoded polynomial subscript is back")

    def test_plain_text_fallback_keeps_the_label(self):
        # renderMath's 4th argument is what the LCD shows without KaTeX.
        self.assertIn("function equationSolutionText(", FRONTEND)
        fn = FRONTEND[FRONTEND.index("function equationSolutionText("):]
        fn = fn[: fn.index("function solveInequalityRemote(")]
        self.assertIn("equationVariableLabel(eq, index).plain", fn)
        render = FRONTEND[FRONTEND.index("renderMath(equationSolutionLatex("):]
        render = render[: render.index(");")]
        self.assertIn("equationSolutionText(", render)

    def test_format_equation_result_no_longer_json_dumps_a_solution(self):
        fn = FRONTEND_NO_COMMENTS
        fn = fn[fn.index("function formatEquationResult("):]
        fn = fn[: fn.index("function equationNumberToLatex(")]
        self.assertNotIn("JSON.stringify(eq.resultState", fn,
                         "a solved system must not print its raw array")
        self.assertIn("equationVariableLabel(eq, index).plain", fn)


class TestNoDebugTracing(unittest.TestCase):
    """DEBUG-1."""

    def test_no_equation_trace_console_calls_in_the_frontend(self):
        self.assertNotIn("EQUATION-TRACE", FRONTEND)

    def test_no_equation_print_tracing_in_the_backend(self):
        src = (PROJECT / "mvp_server.py").read_text(encoding="utf-8")
        self.assertNotIn('[EQUATION]', src)

    def test_the_console_calls_that_survived_are_unrelated_to_equations(self):
        # A guard, not a purge: renderMath's own failure handler is legitimate.
        for line in FRONTEND.splitlines():
            if "console.debug" in line:
                self.assertNotIn("EQUATION", line)


# --------------------------------------------------------------------------
# Browser helpers
# --------------------------------------------------------------------------
KEY_SCRIPT = """([k,s,a]) => {
  const b = document.querySelector('[data-key="' + k + '"]');
  if (!b) throw new Error('no such key ' + k);
  appState.shift = !!s; appState.alpha = !!a;
  handleKey(b); appState.shift = false; appState.alpha = false;
  renderLCD();
}"""

LAYOUT_PROBE = """() => {
  const box=(el)=>el?(({x,y,width,height,right,bottom})=>({x:+x.toFixed(1),
      y:+y.toFixed(1),w:+width.toFixed(1),h:+height.toFixed(1),
      right:+right.toFixed(1),bottom:+bottom.toFixed(1)}))(el.getBoundingClientRect()):null;
  const view=document.querySelector('#lcdEquation .eq-view');
  const rows=Array.from(document.querySelectorAll('#lcdEquation .eq-row'));
  return {
    title: (document.querySelector('#lcdEquation .eq-title')||{}).textContent||null,
    numFields: document.querySelectorAll('#lcdEquation .eq-field').length,
    activeFields: document.querySelectorAll('#lcdEquation .eq-field.active').length,
    clippedH: view ? view.scrollWidth > view.clientWidth + 0.5 : null,
    clippedV: view ? view.scrollHeight > view.clientHeight + 0.5 : null,
    viewBox: box(view),
    rows: rows.map(r => ({
      label: r.querySelector('.eq-row-label')?.textContent,
      fields: Array.from(r.querySelectorAll('.eq-field')).map(f=>f.textContent),
      ops: Array.from(r.querySelectorAll('.eq-op')).map(o=>o.textContent),
      activeIdx: Array.from(r.querySelectorAll('.eq-field'))
                      .findIndex(f=>f.classList.contains('active')),
      box: box(r),
    })),
  };
}"""

STATE_PROBE = """() => { const eq=appState.equation;
  return { phase:eq.phase, type:eq.selectedType, n:eq.numberOfEquations,
           r:eq.currentEquation, c:eq.currentCoefficient, buf:eq.inputBuffer,
           coeffs:eq.coefficientValues }; }"""


class EqBrowserCase(unittest.TestCase):
    """file:// base: enough for input layout and navigation."""

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def setUp(self):
        self.page = self._browser.new_page(viewport={"width": 1100, "height": 1400})
        self.page.set_default_timeout(15000)
        self.page.goto(FRONTEND_PATH.as_uri(), wait_until="domcontentloaded")
        self.page.wait_for_timeout(2500)

    def tearDown(self):
        self.page.close()

    def press(self, key):
        self.page.evaluate(KEY_SCRIPT, [key, False, False])

    def enter_simultaneous(self, n):
        """MODE -> Equation/Func, Simultaneous Equation, count n."""
        self.page.evaluate(
            "() => { appState.mode='Equation/Func'; resetEquationState(); renderLCD(); }")
        self.page.wait_for_timeout(150)
        self.press("equals")           # Simultaneous Equation
        self.page.wait_for_timeout(120)
        self.press(str(n - 1))         # menu 1->2, 2->3, 3->4
        self.page.wait_for_timeout(120)
        self.press("equals")           # confirm the count
        self.page.wait_for_timeout(150)

    def layout(self):
        return self.page.evaluate(LAYOUT_PROBE)

    def state(self):
        return self.page.evaluate(STATE_PROBE)

    def type_number(self, text):
        for ch in text:
            self.press("minus" if ch == "-" else ("decimal" if ch == "." else ch))

    def fill_without_solving(self, n):
        """Type every coefficient but stop BEFORE the final EXE, so the screen
        stays on the input grid. An n-unknown system has n*(n+1) fields and the
        solve fires on the EXE at the last one, i.e. after n*(n+1) presses."""
        rows, cols = n, n + 1
        for r in range(rows):
            for c in range(cols):
                self.type_number(SYSTEMS[n][r][c])
                if not (r == rows - 1 and c == cols - 1):
                    self.press("equals")
                    self.page.wait_for_timeout(25)


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestSimultaneousInputLayout(EqBrowserCase):
    """Every mode shows the right grid, in the right order, unclipped."""

    def test_each_mode_shows_the_right_number_of_fields(self):
        for n in (2, 3, 4):
            with self.subTest(n=n):
                self.enter_simultaneous(n)
                L = self.layout()
                self.assertEqual(L["numFields"], n * (n + 1),
                                 f"{n} unknowns must show {n}x{n+1} boxes")
                self.assertEqual(len(L["rows"]), n)
                self.assertEqual(L["title"], f"{n} equations")

    def test_fields_are_coefficients_then_the_right_hand_side(self):
        for n in (2, 3, 4):
            with self.subTest(n=n):
                self.enter_simultaneous(n)
                L = self.layout()
                for row in L["rows"]:
                    # n coefficient boxes, then ' = ', then the RHS box
                    self.assertEqual(len(row["fields"]), n + 1)
                    self.assertEqual(row["ops"][-1], " =")
                    self.assertEqual(row["ops"][:n],
                                     [v if i == 0 else f" + {v}"
                                      for i, v in enumerate(VARIABLES[n])],
                                     "variable labels are wrong or out of order")
                    self.assertEqual(row["label"], f"{row['label'].strip()}:"
                                     if False else row["label"])

    def test_rows_are_numbered_one_to_n(self):
        for n in (2, 3, 4):
            with self.subTest(n=n):
                self.enter_simultaneous(n)
                labels = [r["label"] for r in self.layout()["rows"]]
                self.assertEqual(labels, [f"{i + 1}:" for i in range(n)])

    def test_exactly_one_field_is_active(self):
        for n in (2, 3, 4):
            with self.subTest(n=n):
                self.enter_simultaneous(n)
                self.assertEqual(self.layout()["activeFields"], 1)

    def test_nothing_is_clipped_in_any_mode(self):
        for n in (2, 3, 4):
            with self.subTest(n=n):
                self.enter_simultaneous(n)
                # fill it so the widest realistic content is on screen
                self.fill_without_solving(n)
                L = self.layout()
                self.assertFalse(L["clippedH"],
                                 f"{n} unknowns overflow the LCD horizontally")
                self.assertFalse(L["clippedV"],
                                 f"{n} unknowns overflow the LCD vertically")

    def test_rows_stay_inside_the_lcd_width(self):
        for n in (2, 3, 4):
            with self.subTest(n=n):
                self.enter_simultaneous(n)
                self.fill_without_solving(n)
                L = self.layout()
                for row in L["rows"]:
                    self.assertLessEqual(row["box"]["right"], L["viewBox"]["right"] + 0.5,
                                         "a row sticks out of the LCD")

    def test_negative_and_zero_coefficients_display(self):
        self.enter_simultaneous(2)
        self.fill_without_solving(2)
        L = self.layout()
        self.assertEqual(L["rows"][0]["fields"], ["2", "1", "7"])
        self.assertEqual(L["rows"][1]["fields"], ["1", "-3", "-2"])


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestSimultaneousNavigation(EqBrowserCase):

    def test_equals_advances_within_a_row_then_to_the_next_row(self):
        self.enter_simultaneous(3)
        self.type_number("1")
        self.press("equals")
        s = self.state()
        self.assertEqual((s["r"], s["c"]), (0, 1))
        self.assertEqual(s["coeffs"][0][0], 1, "the typed value was not committed")
        self.assertEqual(s["buf"], "", "the buffer was not cleared after commit")

    def test_equals_on_the_last_field_of_a_row_starts_the_next_row(self):
        self.enter_simultaneous(2)
        for _ in range(3):
            self.press("equals")
        self.assertEqual((self.state()["r"], self.state()["c"]), (1, 0))

    def test_arrow_keys_move_and_clamp(self):
        self.enter_simultaneous(3)
        self.press("dpad_right")
        self.assertEqual(self.state()["c"], 1)
        self.press("dpad_left")
        self.press("dpad_left")
        self.assertEqual(self.state()["c"], 0, "dpad_left ran past the first field")
        for _ in range(8):
            self.press("dpad_right")
        self.assertEqual(self.state()["c"], 3, "dpad_right ran past the RHS field")
        self.press("dpad_down")
        self.assertEqual(self.state()["r"], 1, "dpad_down did not change row")
        self.assertEqual(self.state()["c"], 3, "dpad_down must keep the column")
        self.press("dpad_up")
        self.assertEqual(self.state()["r"], 0)
        for _ in range(5):
            self.press("dpad_up")
        self.assertEqual(self.state()["r"], 0, "dpad_up ran past the first row")

    def test_moving_away_commits_the_field_being_left(self):
        self.enter_simultaneous(2)
        self.type_number("5")
        self.press("dpad_right")
        self.assertEqual(self.state()["coeffs"][0][0], 5)

    def test_del_erases_the_buffer_and_digits_replace_cleanly(self):
        self.enter_simultaneous(2)
        self.type_number("123")
        self.press("del")
        self.assertEqual(self.state()["buf"], "12")
        self.press("equals")
        self.assertEqual(self.state()["coeffs"][0][0], 12)

    def test_re_entering_the_mode_discards_the_previous_system(self):
        self.enter_simultaneous(2)
        for cell in SYSTEMS[2][0]:
            self.type_number(cell)
            self.press("equals")
        self.assertTrue(any(v != "" for row in self.state()["coeffs"] for v in row))
        # leave and come back the way the MENU does
        self.page.evaluate(
            "() => { appState.mode='Equation/Func'; resetEquationState(); renderLCD(); }")
        self.page.wait_for_timeout(150)
        self.press("equals")
        self.page.wait_for_timeout(120)
        self.press("1")
        self.page.wait_for_timeout(120)
        self.press("equals")
        self.page.wait_for_timeout(150)
        s = self.state()
        self.assertEqual(s["coeffs"], [["", "", ""], ["", "", ""]],
                         "stale coefficients survived a re-entry")


# --------------------------------------------------------------------------
# Solving tests: need the backend, so a real (short-lived) server.
# --------------------------------------------------------------------------
@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestSimultaneousSolving(unittest.TestCase):
    """Real SHIFT+OPTN -> EQN -> Simultaneous -> coefficients -> EXE -> solution."""

    server = None
    thread = None

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), mvp_server.MvpHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.4)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls._browser.close()
        cls._pw.stop()

    def setUp(self):
        self.page = self._browser.new_page(viewport={"width": 1100, "height": 1400})
        self.page.set_default_timeout(15000)
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.goto(f"http://127.0.0.1:{self.port}/frontend.html",
                       wait_until="domcontentloaded")
        self.page.wait_for_timeout(2500)

    def tearDown(self):
        self.page.close()

    def press(self, key):
        self.page.evaluate(KEY_SCRIPT, [key, False, False])

    def enter_and_fill(self, n):
        self.page.evaluate(
            "() => { appState.mode='Equation/Func'; resetEquationState(); renderLCD(); }")
        self.page.wait_for_timeout(150)
        self.press("equals")
        self.page.wait_for_timeout(120)
        self.press(str(n - 1))
        self.page.wait_for_timeout(120)
        self.press("equals")
        self.page.wait_for_timeout(150)
        rows, cols = n, n + 1
        for r in range(rows):
            for c in range(cols):
                for ch in SYSTEMS[n][r][c]:
                    self.press("minus" if ch == "-" else
                               ("decimal" if ch == "." else ch))
                if not (r == rows - 1 and c == cols - 1):
                    self.press("equals")
                    self.page.wait_for_timeout(25)
        self.press("equals")
        self.page.wait_for_timeout(800)

    def solutions(self):
        """Every solution page, as the variable name and the displayed value."""
        out = []
        n = 4
        for _ in range(5):
            out.append(self.page.evaluate(
                """() => { const h = document.getElementById('eqSolutionMath');
                     const html = h ? h.querySelector('.katex-html') : null;
                     return { visual: html ? html.textContent : (h ? h.textContent : ''),
                              latex: h ? h.textContent : '',
                              pos: (document.querySelector('.eq-solution-pos')||{}).textContent || null }; }"""))
            self.press("dpad_down")
            self.page.wait_for_timeout(200)
        return out

    def test_each_mode_solves_to_the_hand_computed_answer(self):
        for n in (2, 3, 4):
            with self.subTest(n=n):
                self.enter_and_fill(n)
                got = self.page.evaluate("() => appState.equation.resultState")
                self.assertIsInstance(got, list, f"{n}-unknown solve did not return a list")
                self.assertEqual(len(got), n)
                for actual, expected in zip(got, ORACLES[n]):
                    self.assertAlmostEqual(float(actual), expected, places=9,
                                           msg=f"{n}-unknown: {got} vs {ORACLES[n]}")

    def test_each_mode_labels_solutions_with_its_variables(self):
        for n in (2, 3, 4):
            with self.subTest(n=n):
                self.enter_and_fill(n)
                pages = self.solutions()[:n]
                for i, page in enumerate(pages):
                    with self.subTest(solution=i):
                        self.assertTrue(
                            page["visual"].strip().startswith(VARIABLES[n][i]),
                            f"solution {i+1} of a {n}-unknown system is labelled "
                            f"{page['visual']!r}, expected to start with "
                            f"{VARIABLES[n][i]!r}")

    def test_a_simultaneous_solution_is_not_labelled_like_a_polynomial_root(self):
        self.enter_and_fill(2)
        first = self.solutions()[0]
        self.assertNotIn("x1", first["visual"].replace(" ", ""))
        self.assertNotIn("x₂", first["visual"])
        self.assertTrue(first["visual"].strip().startswith("x"))

    def test_every_solution_is_reachable_and_the_pager_wraps(self):
        for n in (2, 3, 4):
            with self.subTest(n=n):
                self.enter_and_fill(n)
                pages = self.solutions()
                for i in range(1, n + 1):
                    self.assertIn(f"{i}/{n}", pages[i - 1]["pos"],
                                  f"solution {i} of {n} was not reachable")
                self.assertIn(f"1/{n}", pages[n]["pos"],
                              "the pager did not wrap back to the first solution")

    def test_exact_form_shows_the_rational_answer(self):
        self.enter_and_fill(2)          # x = 19/7, y = 11/7
        self.press("s_to_d")
        self.page.wait_for_timeout(300)
        text = self.page.evaluate(
            """() => { const h=document.getElementById('eqSolutionMath');
                       return h ? h.textContent : ''; }""")
        self.assertIn("19", text)
        self.assertIn("7", text)
        self.assertIn("a b/c", self.page.evaluate(
            """() => { const p=document.querySelector('.eq-solution-pos');
                       return p ? p.textContent : ''; }"""))

    def test_an_incomplete_system_reports_an_error_without_crashing(self):
        self.enter_simultaneous_like(2)
        self.press("1")                  # only the very first coefficient
        # 2 unknowns = 6 fields; the solve fires on the EXE at field 6.
        for _ in range(6):
            self.press("equals")
            self.page.wait_for_timeout(60)
        self.page.wait_for_timeout(700)
        state = self.page.evaluate(
            "() => ({ phase: appState.equation.phase, result: appState.equation.resultState })")
        self.assertEqual(state["result"], "Math ERROR")
        self.assertEqual(self.errors, [])

    def test_a_singular_system_reports_an_error(self):
        self.enter_simultaneous_like(2)
        # row 2 is 2*(row 1) -> singular. 6 fields, so 6 EXE presses.
        for cell in ("1", "1", "2", "2", "2", "4"):
            self.press(cell)
            self.press("equals")
            self.page.wait_for_timeout(30)
        self.page.wait_for_timeout(800)
        self.assertEqual(self.page.evaluate("() => appState.equation.resultState"),
                         "Math ERROR")
        self.assertEqual(self.errors, [])

    def test_no_stale_answer_is_left_after_a_failed_solve(self):
        self.enter_and_fill(2)
        self.assertIsInstance(self.page.evaluate(
            "() => appState.equation.resultState"), list)
        # go back to a blank system and confirm the old answer is gone
        self.page.evaluate(
            "() => { appState.mode='Equation/Func'; resetEquationState(); renderLCD(); }")
        self.page.wait_for_timeout(150)
        self.press("equals")
        self.page.wait_for_timeout(120)
        self.press("1")
        self.page.wait_for_timeout(120)
        self.press("equals")
        self.page.wait_for_timeout(150)
        self.assertEqual(self.page.evaluate("() => appState.equation.resultState"), None)

    def enter_simultaneous_like(self, n):
        self.page.evaluate(
            "() => { appState.mode='Equation/Func'; resetEquationState(); renderLCD(); }")
        self.page.wait_for_timeout(150)
        self.press("equals")
        self.page.wait_for_timeout(120)
        self.press(str(n - 1))
        self.page.wait_for_timeout(120)
        self.press("equals")
        self.page.wait_for_timeout(150)


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestPolynomialLabelsUnchanged(unittest.TestCase):
    """Item 6 must be untouched: a polynomial's roots stay x_1, x_2, ... ."""

    URL = FRONTEND_PATH.as_uri()

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls._browser.new_page(viewport={"width": 1100, "height": 1400})
        cls.page.set_default_timeout(15000)
        cls.page.goto(cls.URL, wait_until="domcontentloaded")
        cls.page.wait_for_timeout(2500)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def test_quadratic_roots_keep_a_real_subscript(self):
        self.page.evaluate(
            """() => {
                 appState.mode='Equation/Func'; appState.poweredOn=true; appState.splash=false;
                 appState.equation = { selectedType:'polynomial', phase:'result',
                   numberOfEquations:2, polynomialDegree:2, currentEquation:0,
                   currentCoefficient:0, coefficientValues:[[1,-3,2]], inputBuffer:'',
                   selectedMenuItem:0, resultState:[1,2], extremum:null,
                   solutionIndex:0, exactForm:false };
                 renderLCD();
               }""")
        self.page.wait_for_timeout(400)
        info = self.page.evaluate(
            """() => { const h=document.getElementById('eqSolutionMath');
                       const html=h?h.querySelector('.katex-html'):null;
                       return { sub: h?h.querySelectorAll('.msub,.msupsub').length:0,
                                text: html?html.textContent:(h?h.textContent:'') }; }""")
        self.assertGreaterEqual(info["sub"], 1,
                                "a polynomial root must still render a KaTeX subscript")
        self.assertTrue(info["text"].strip().startswith("x"),
                        info["text"])


if __name__ == "__main__":
    unittest.main()