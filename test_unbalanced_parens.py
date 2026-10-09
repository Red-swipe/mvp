"""Item 10 regression coverage: unbalanced opening parentheses are closed on EXE.

Defect this locks down: the fx-991EX closes what the user left open before it
evaluates -- `(2+3` + EXE shows (2+3) and answers 5. Nothing did that here, so
every unbalanced expression died in the evaluator's parser and the LCD showed
`Math ERROR`: `(2+3`, `((2+3)*4`, `((2+3)*(4+5`, `sin(30` and `sin(cos(0` all
failed.

Where the fix lives and why. The closers are appended to the MODEL (rootSlot),
not to the outgoing string, and the hook sits in evaluate() -- the single EXE
entry point that serves both the file:// bridge and the /api/key call. The
expression line is re-rendered from rootSlot, so a string-only fix would leave
the screen showing `(2+3` while the engine answered for `(2+3)`.

Structural safety. Only LITERAL string items are counted: serializeSlot emits
every template's own parentheses in balanced pairs, so the only unbalanced
parentheses in the tree are the ones typed on the `(` key or arriving inside a
raw function token such as `sin(`. A closer is also appended to the SLOT that
holds its own `(`, which is what puts the `)` inside a fraction's denominator
box rather than floating outside the template.

The counter must never repair an over-closed expression: `2+3)` and `(2+3))`
keep their Math ERROR, and `2+` (nothing left open) is untouched too.

Static layer: the helper exists and is wired into evaluate(). Browser layer: the
real rendered DOM for every case, driven through handleKey + the equals key.
Loads frontend.html over file:// -- no server.
"""
import pathlib
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


class TestBalancingWiring(unittest.TestCase):
    """The helper exists, is model-based, and runs on the real EXE path."""

    def test_helper_exists(self):
        self.assertIn("function unclosedParenSlots(", FRONTEND)
        self.assertIn("function closeUnbalancedParens(", FRONTEND)

    def test_exe_calls_the_helper_before_serializing(self):
        # Must run BEFORE getExpr(), otherwise the LCD and the evaluated
        # expression would be two different strings.
        seg = FRONTEND[FRONTEND.index("async function evaluate()"):]
        seg = seg[: seg.index("const evalExpr =")]
        self.assertLess(seg.index("closeUnbalancedParens()"),
                        seg.index("const expr = getExpr()"))

    def test_only_literal_string_items_are_counted(self):
        # Templates emit balanced parentheses by construction, so they must be
        # skipped rather than counted.
        fn = FRONTEND[FRONTEND.index("function unclosedParenSlots("):]
        fn = fn[: fn.index("function closeUnbalancedParens(")]
        self.assertIn("if (typeof item === 'string')", fn)
        self.assertIn("for (const k of SLOT_KEYS)", fn)

    def test_over_closed_expressions_are_never_repaired(self):
        # Popping on ')' leaves an empty stack for `2+3)`, so nothing is appended
        # and the established Math ERROR survives.
        fn = FRONTEND[FRONTEND.index("function unclosedParenSlots("):]
        fn = fn[: fn.index("function closeUnbalancedParens(")]
        self.assertIn("else if (ch === ')') stack.pop();", fn)
        close = FRONTEND[FRONTEND.index("function closeUnbalancedParens("):]
        close = close[: close.index("function prepareExpressionForEvaluation(")]
        self.assertIn("if (!stack.length) return 0;", close)


@unittest.skipUnless(HAVE_BROWSER, "Playwright + Chrome are required")
class TestAutoCloseOnExe(unittest.TestCase):
    URL = FRONTEND_PATH.as_uri()

    @classmethod
    def setUpClass(cls):
        cls._pw = sync_playwright().start()
        cls._browser = cls._pw.chromium.launch(channel="chrome")
        cls.page = cls._browser.new_page(viewport={"width": 1000, "height": 1300})
        cls.page.set_default_timeout(10000)
        cls.page.goto(cls.URL, wait_until="domcontentloaded")
        cls.page.wait_for_timeout(2500)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._pw.stop()

    def setUp(self):
        self.page.evaluate(
            """() => { resetExpr(); appState.shift = false; appState.alpha = false;
                 appState.resultDisplayed = false; appState.result = null;
                 appState.error = null; appState.lastAnswer = '0';
                 appState.settings.angleUnit = 'Degree';
                 appState.settings.inputOutput = 'LineO';
                 appState.settings.fractionResult = 'd/c';
                 renderLCD(); }""")

    # -- helpers ---------------------------------------------------------
    def press(self, key):
        self.page.evaluate(
            """(k) => { const b = document.querySelector('[data-key="' + k + '"]');
                 if (!b) throw new Error('no such key: ' + k);
                 appState.shift = false; appState.alpha = false;
                 handleKey(b); renderLCD(); }""", key)

    def press_shift(self, key):
        self.page.evaluate(
            """(k) => { const b = document.querySelector('[data-key="' + k + '"]');
                 appState.shift = true; appState.alpha = false;
                 handleKey(b); appState.shift = false; renderLCD(); }""", key)

    def enter(self, keys):
        for k in keys:
            self.press(k)

    def exe(self):
        self.page.evaluate(
            """() => { const b = document.querySelector('[data-key="equals"]');
                 appState.shift = false; appState.alpha = false;
                 handleKey(b); renderLCD(); }""")
        self.page.wait_for_timeout(200)
        return self.page.evaluate(
            """() => ({ expr: getExpr(),
                       payload: prepareExpressionForEvaluation(getExpr()),
                       result: appState.result, error: appState.error,
                       lcdExpr: document.getElementById('lcdExprContent')
                                    .innerText,
                       lcdResult: document.getElementById('lcdResultLine')
                                    .innerText,
                       state: currentScreenState() })""")

    @staticmethod
    def norm(text):
        """The LCD draws the display glyphs (U+00D7, U+2212) and wraps the
        expression in a caret box; the serialized form uses `*` and `-`."""
        return (text.replace("□", "").replace("×", "*").replace("−", "-")
                    .replace("⁻¹", "^(-1)").replace(" ", "").replace("\n", ""))

    def assertClosesTo(self, keys, entered, expected_expr, expected_result):
        self.enter(keys)
        self.assertEqual(self.page.evaluate("() => getExpr()"), entered,
                         "the test did not build the expression it meant to")
        got = self.exe()
        self.assertIsNone(got["error"], f"{entered!r} raised {got['error']!r}")
        self.assertEqual(got["expr"], expected_expr,
                         f"{entered!r} completed to {got['expr']!r}")
        # The LCD must show the COMPLETED expression -- never the original while
        # a different one is evaluated.
        self.assertEqual(self.norm(got["lcdExpr"]), self.norm(expected_expr),
                         f"LCD shows {got['lcdExpr']!r}, not the completed expression")
        # Whatever goes to /api/key is the same completed expression.
        self.assertEqual(got["payload"], expected_expr)
        self.assertAlmostEqual(float(got["result"]), expected_result, places=9,
                               msg=f"{entered!r} -> {got['result']!r}")
        return got

    # -- A. basic --------------------------------------------------------
    def test_simple_unbalanced_group_is_closed(self):
        self.assertClosesTo(["left_paren", "2", "plus", "3"],
                            "(2+3", "(2+3)", 5.0)

    def test_subtraction_group_is_closed(self):
        self.assertClosesTo(["left_paren", "8", "minus", "3"],
                            "(8-3", "(8-3)", 5.0)

    def test_balanced_and_plain_expressions_are_untouched(self):
        self.assertClosesTo(["2", "plus", "3"], "2+3", "2+3", 5.0)
        self.assertClosesTo(["left_paren", "2", "plus", "3", "right_paren"],
                            "(2+3)", "(2+3)", 5.0)

    # -- B. nesting ------------------------------------------------------
    def test_nested_group_with_a_trailing_operand(self):
        self.assertClosesTo(["left_paren", "left_paren", "2", "plus", "3",
                             "right_paren", "multiply", "4"],
                            "((2+3)*4", "((2+3)*4)", 20.0)

    def test_two_missing_closers_in_different_groups(self):
        self.assertClosesTo(["left_paren", "left_paren", "2", "plus", "3",
                             "right_paren", "multiply", "left_paren", "4",
                             "plus", "5"],
                            "((2+3)*(4+5", "((2+3)*(4+5))", 45.0)

    def test_three_deep_group_is_closed(self):
        self.assertClosesTo(["left_paren", "left_paren", "left_paren",
                             "2", "plus", "3", "right_paren"],
                            "(((2+3)", "(((2+3)))", 5.0)

    def test_balanced_nested_expression_is_untouched(self):
        self.assertClosesTo(["left_paren", "left_paren", "2", "plus", "3",
                             "right_paren", "multiply", "4", "right_paren"],
                            "((2+3)*4)", "((2+3)*4)", 20.0)

    # -- C. function tokens ----------------------------------------------
    def test_unclosed_sine_argument_is_closed(self):
        # The `sin` key inserts the raw token `sin(`, so this is an unbalanced
        # opening produced by a real key -- not a hand-typed string.
        self.assertClosesTo(["sin", "3", "0"], "sin(30", "sin(30)", 0.5)

    def test_nested_function_call_is_closed(self):
        # sin(cos(0) in Degree = sin(1 deg).
        self.assertClosesTo(["sin", "cos", "0"], "sin(cos(0", "sin(cos(0))",
                            0.01745240644)

    def test_unclosed_natural_log_is_closed(self):
        self.assertClosesTo(["ln", "1", "0", "0"], "ln(100", "ln(100)",
                            4.605170186)

    def test_base_log_template_is_unaffected(self):
        # `log` is a base/argument template, not a bare `log(`, so the
        # `log(100` -> 2 requirement maps to log_base(10,100).
        self.enter(["log", "dpad_right", "1", "0", "0"])
        self.assertEqual(self.page.evaluate("() => getExpr()"), "log_base(10,100)")
        got = self.exe()
        self.assertEqual(got["expr"], "log_base(10,100)")
        self.assertEqual(str(got["result"]), "2")

    def test_sqrt_template_still_round_trips(self):
        # Template-generated parentheses are already balanced: nothing added.
        self.enter(["sqrt", "2", "5"])
        self.assertEqual(self.page.evaluate("() => getExpr()"), "sqrt(25)")
        got = self.exe()
        self.assertEqual(got["expr"], "sqrt(25)")
        self.assertEqual(str(got["result"]), "5")

    def test_closer_lands_in_the_slot_that_owns_the_open_paren(self):
        # A '(' typed inside a fraction's denominator must be closed INSIDE that
        # denominator box, not appended after the whole template.
        self.enter(["fraction", "2", "dpad_right", "left_paren", "3"])
        self.assertEqual(self.page.evaluate("() => getExpr()"), "((2)/((3))")
        got = self.exe()
        self.assertEqual(got["expr"], "((2)/((3)))")
        # Both the numerator and the completed denominator are live slots; the
        # closer is inside the denominator box, not after the template.
        slots = self.page.eval_on_selector_all(
            "#lcdExprContent [data-slot-id]", "els => els.map(e => e.textContent)")
        self.assertEqual(sorted(slots), ["(3)", "2"],
                         "the closer did not land in the denominator slot")
        self.assertAlmostEqual(float(got["result"]), 2.0 / 3.0, places=9)

    # -- D. already balanced ---------------------------------------------
    def test_already_balanced_expressions_are_not_modified(self):
        for keys, entered in (
                (["left_paren", "2", "plus", "3", "right_paren"], "(2+3)"),
                (["left_paren", "left_paren", "2", "plus", "3",
                  "right_paren", "multiply", "4", "right_paren"], "((2+3)*4)"),
                (["sin", "3", "0", "right_paren"], "sin(30)"),
                (["sin", "left_paren", "3", "0", "plus", "3", "0",
                  "right_paren", "right_paren"], "sin((30+30))"),
        ):
            with self.subTest(entered=entered):
                self.enter(keys)
                self.assertEqual(self.page.evaluate("() => getExpr()"), entered)
                got = self.exe()
                self.assertEqual(got["expr"], entered,
                                 "a balanced expression was needlessly modified")
                self.assertIsNone(got["error"])
                self.assertEqual(self.norm(got["lcdExpr"]), self.norm(entered))

    # -- E. excess closing -----------------------------------------------
    def test_excess_closing_parenthesis_still_errors(self):
        for keys, entered in ((["2", "plus", "3", "right_paren"], "2+3)"),
                              (["left_paren", "2", "plus", "3", "right_paren",
                                "right_paren"], "(2+3))")):
            with self.subTest(entered=entered):
                self.enter(keys)
                self.assertEqual(self.page.evaluate("() => getExpr()"), entered)
                got = self.exe()
                self.assertEqual(got["error"], "Math ERROR",
                                 f"{entered!r} was silently repaired")
                self.assertEqual(got["expr"], entered,
                                 "an over-closed expression must not be rewritten")
                self.assertIsNone(got["result"])
                self.assertEqual(got["state"], "ERROR")

    # -- F. malformed / boundary -----------------------------------------
    def test_incomplete_operator_is_not_repaired(self):
        # Nothing is left open, so auto-closing must not touch it at all.
        self.enter(["2", "plus"])
        self.assertEqual(self.page.evaluate("() => getExpr()"), "2+")
        got = self.exe()
        self.assertEqual(got["expr"], "2+")
        self.assertEqual(got["error"], "Math ERROR")

    def test_a_lone_open_paren_still_errors(self):
        # `(` -> `()` is a completion, but an empty group is still invalid and
        # must not be turned into a valid expression.
        self.enter(["left_paren"])
        self.assertEqual(self.page.evaluate("() => getExpr()"), "(")
        got = self.exe()
        self.assertEqual(got["expr"], "()")
        self.assertEqual(got["error"], "Math ERROR")
        self.assertIsNone(got["result"])

    def test_group_with_a_single_operand_is_completed(self):
        self.assertClosesTo(["left_paren", "2"], "(2", "(2)", 2.0)

    def test_empty_expression_does_not_evaluate(self):
        got = self.exe()
        self.assertIsNone(got["result"])
        self.assertIsNone(got["error"])
        self.assertEqual(got["expr"], "")

    def test_completed_expression_survives_a_second_exe(self):
        # The caret must end up behind the inserted closers, so pressing EXE
        # again re-evaluates the completed expression rather than overwriting a
        # closer and re-deriving a different, wrong one.
        self.enter(["left_paren", "2", "plus", "3"])
        first = self.exe()
        self.assertEqual(first["result"], "5")
        second = self.exe()
        self.assertIsNone(second["error"], second)
        self.assertEqual(second["expr"], "(2+3)")
        self.assertEqual(str(second["result"]), "5")

    def test_typing_after_an_auto_close_continues_the_expression(self):
        # `(` 2 + 3 EXE -> 5, then `+4` EXE must continue from the completed
        # group instead of landing inside it.
        self.enter(["left_paren", "2", "plus", "3"])
        self.assertEqual(str(self.exe()["result"]), "5")
        self.enter(["plus", "4"])
        got = self.exe()
        self.assertIsNone(got["error"], got)
        self.assertAlmostEqual(float(got["result"]), 9.0, places=9)


class TestBackendAcceptsTheCompletedForm(unittest.TestCase):
    """The engine side of the boundary, without starting a server.

    frontend.html always posts the completed string, so the evaluator must
    accept exactly what the frontend produces -- this is the same
    safe_evaluate_expression() that /api/key calls.
    """

    def test_engine_evaluates_the_completed_forms(self):
        import mvp_server

        for expr, expected in (("(2+3)", 5.0), ("((2+3)*4)", 20.0),
                               ("((2+3)*(4+5))", 45.0), ("(((2+3)))", 5.0),
                               ("sin(30)", 0.5),
                               ("log_base(10,100)", 2.0)):
            with self.subTest(expr=expr):
                got = mvp_server.safe_evaluate_expression(expr, 0.0, "Degree")
                self.assertAlmostEqual(float(got), expected, places=9,
                                       msg=f"{expr} -> {got}")

    def test_engine_still_rejects_the_uncompleted_forms(self):
        # The engine is left strict on purpose: the completion is a UI
        # behaviour, not a parser change, so nothing downstream starts silently
        # accepting half-typed input.
        import mvp_server

        for expr in ("(2+3", "((2+3)*4", "2+3)", "(2+3))", "2+"):
            with self.subTest(expr=expr):
                with self.assertRaises(Exception, msg=expr):
                    mvp_server.safe_evaluate_expression(expr, 0.0, "Degree")


if __name__ == "__main__":
    unittest.main()