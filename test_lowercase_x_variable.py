"""Regression tests for BUG-01 / BUG-02: the lowercase `x` calculator variable.

BUG-01: the keypad `x` key (and its ALPHA + `)` label) inserted a lowercase
`x`, but the backend only substituted the canonical uppercase variable names
(A B C D E F M X Y), so `x+1` failed with
`Math ERROR: Unexpected character 'x' at position 0`.

BUG-02: `/api/solve` upper-cased the *target variable* argument but not the
*expression*, so a SOLVE equation built on the keypad (which contained the
lowercase `x`) always failed.

The fix makes the canonical uppercase `X` the single source of truth:
 - the frontend inserts `X` (matching every other ALPHA variable), and
 - the backend additionally accepts lowercase `x`/`y` as an alias for the X/Y
   variables, substituted AFTER special-function reduction so a `x` bound as
   the dummy variable of integral()/sigma()/diff() is never clobbered.

Layers covered here:
 1. direct evaluator      - lowercase/uppercase X agree, errors preserved
 2. bound-variable guard  - integral/sigma/diff still bind `x` themselves
 3. SOLVE                 - `x+1=6` and the existing uppercase case
 4. frontend routing      - real routing source executed in node
 5. frontend ALPHA wiring - button labels/attributes in frontend.html
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from mvp_server import CalculatorController, safe_evaluate_expression

PROJECT = Path(__file__).resolve().parent
FRONTEND = (PROJECT / "frontend.html").read_text(encoding="utf-8")

# All nine canonical calculator variables, as seeded by the controller.
VARS = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0,
        "F": 0.0, "M": 0.0, "X": 0.0, "Y": 0.0}

# X=5, Y=2 so lowercase and uppercase forms are distinguishable by result.
XV = {**VARS, "X": 5.0, "Y": 2.0}


def ev(expr, variables=None):
    return safe_evaluate_expression(
        expr, 0.0, "Degree", dict(XV if variables is None else variables))


class TestEvaluatorVariableSpellings(unittest.TestCase):
    """1. X+1 / x+1 with X=5 -> 6, and existing uppercase behaviour intact."""

    def test_uppercase_x_unchanged(self):
        self.assertAlmostEqual(ev("X+1"), 6.0)

    def test_lowercase_x_matches_uppercase(self):
        # BUG-01
        self.assertAlmostEqual(ev("x+1"), 6.0)

    def test_all_x_spellings_agree(self):
        for expr in ("X", "x", "X+1", "x+1", "X*2", "x*2", "(X+1)*2", "(x+1)*2",
                     "X/2", "x/2"):
            self.assertAlmostEqual(
                ev(expr), ev(expr.replace("x", "X")), msg=expr)

    def test_y_spellings_agree(self):
        for expr in ("Y", "y", "Y+1", "y+1", "Y*3", "y*3"):
            self.assertAlmostEqual(
                ev(expr), ev(expr.replace("y", "Y")), msg=expr)

    def test_existing_uppercase_variables_unchanged(self):
        for name in ("A", "B", "C", "D", "E", "F", "M"):
            self.assertAlmostEqual(
                ev(f"{name}*2", {**VARS, name: 4}), 8.0, msg=name)

    def test_x_inside_function_is_the_variable(self):
        # `x` is the X variable unless a function binds it itself.
        self.assertAlmostEqual(ev("sqrt(x)"), math_sqrt(5.0))
        self.assertAlmostEqual(ev("ln(x)"), math_log(5.0))
        self.assertAlmostEqual(ev("x!"), 120.0)          # 5!
        self.assertAlmostEqual(ev("10^x"), 100000.0)      # 10**5
        self.assertAlmostEqual(ev("e^x"), math_e_pow(5.0))

    def test_names_containing_x_are_not_substituted(self):
        # `xroot` must survive intact, not become `5root`.
        self.assertAlmostEqual(ev("xroot(3,8)"), 2.0)
        self.assertAlmostEqual(ev("cbrt(27)"), 3.0)


class TestArbitraryIdentifiersRejected(unittest.TestCase):
    """2. The fix must not turn the evaluator into a lowercase-identifier
    parser: undefined variables and unknown names still raise."""

    def test_undefined_uppercase_variable_still_errors(self):
        for name in ("Z", "Q", "G", "N"):
            with self.assertRaises(Exception, msg=name):
                ev(f"{name}+1", VARS)

    def test_undefined_lowercase_identifier_still_errors(self):
        for name in ("q", "z", "w", "n", "foo", "xyz", "xx", "yy"):
            with self.assertRaises(Exception, msg=name):
                ev(f"{name}+1", VARS)

    def test_lowercase_alias_ignored_when_variable_absent(self):
        # No 'X' key at all -> lowercase `x` must not resolve to something.
        with self.assertRaises(Exception):
            ev("x+1", {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0,
                       "E": 0.0, "F": 0.0, "M": 0.0})

    def test_set_variable_allowlist(self):
        ctrl = CalculatorController()
        # Lowercase input canonicalises to the uppercase slot.
        r = ctrl.set_variable("x", 5)
        self.assertTrue(r["ok"])
        self.assertEqual(r["variable"], "X")
        self.assertAlmostEqual(
            safe_evaluate_expression("x+1", 0.0, "Degree", ctrl.variables), 6.0)
        # Anything outside the nine variables is still refused.
        for bad in ("Z", "z", "Q", "1", "XY"):
            self.assertFalse(ctrl.set_variable(bad, 1)["ok"], msg=bad)

    def test_seed_uses_canonical_names(self):
        # The old seed held lowercase "x"/"y", which nothing ever read.
        self.assertEqual(set(CalculatorController().variables),
                         {"A", "B", "C", "D", "E", "F", "M", "X", "Y"})


class TestBoundDummyVariablePreserved(unittest.TestCase):
    """3. integral()/sigma()/diff() bind `x` themselves. The lowercase alias
    runs after special-function reduction precisely so it cannot steal it."""

    def test_integral(self):
        self.assertAlmostEqual(ev("integral(sqrt(x),0,1)"), 2 / 3, places=3)
        self.assertAlmostEqual(ev("integral(x^2,0,1)"), 1 / 3, places=3)
        self.assertAlmostEqual(ev("sigma(x,1,5)"), 15.0)
        self.assertAlmostEqual(ev("Σ(x,1,5)"), 15.0)

    def test_diff_keypad_template(self):
        self.assertAlmostEqual(ev("diff(x^2,3)"), 6.0, places=3)
        self.assertAlmostEqual(ev("d/dx(x^2,3)"), 6.0, places=3)

    def test_dummy_binds_even_with_x_set(self):
        # X=5 must not leak into the integrator's dummy variable.
        self.assertAlmostEqual(
            ev("integral(x,0,1)"), 0.5, places=3)
        self.assertAlmostEqual(
            ev("diff(x^2,1)"), 2.0, places=3)


class TestSolve(unittest.TestCase):
    """4. BUG-02: SOLVE over a lowercase-x equation."""

    def setUp(self):
        self.ctrl = CalculatorController()

    def test_solve_lowercase_x_equation(self):
        r = self.ctrl.solve_equation_newton("x+1=6", "X", 0.0)
        self.assertTrue(r["ok"], r)
        self.assertAlmostEqual(float(r["result"]), 5.0, places=5)

    def test_solve_uppercase_x_equation_no_regression(self):
        r = self.ctrl.solve_equation_newton("X+1=6", "X", 0.0)
        self.assertTrue(r["ok"], r)
        self.assertAlmostEqual(float(r["result"]), 5.0, places=5)

    def test_solve_both_spellings_agree(self):
        for lower, upper in (("x+1=6", "X+1=6"),
                             ("x^2=9", "X^2=9"),
                             ("x^2-4=0", "X^2-4=0")):
            a = self.ctrl.solve_equation_newton(lower, "X", 0.0)
            b = self.ctrl.solve_equation_newton(upper, "X", 0.0)
            self.assertTrue(a["ok"], a)
            self.assertTrue(b["ok"], b)
            self.assertAlmostEqual(float(a["result"]), float(b["result"]),
                                   places=5, msg=lower)

    def test_solve_lowercase_x_exponent(self):
        r = self.ctrl.solve_equation_newton("2^x=8", "X", 0.0)
        self.assertTrue(r["ok"], r)
        self.assertAlmostEqual(float(r["result"]), 3.0, places=5)

    def test_solve_calc_agree(self):
        # SHIFT+CALC (calc_evaluate) and SHIFT+SOLVE must both read X.
        r = self.ctrl.calc_evaluate("x+1", {"X": 5})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["result"], "6")

    def test_solve_non_convergence_still_errors(self):
        r = self.ctrl.solve_equation_newton("X^2+1", "X", 0.0)
        self.assertFalse(r["ok"])


# ── frontend ────────────────────────────────────────────────────────────────

# Routing branches under test, sliced verbatim out of frontend.html. Each slice
# runs inside a stubbed function so the real `if (rawKey === ...)` code decides
# which token is inserted.
ROUTE_SLICES = [
    ("ellipsis", "if (rawKey === 'ellipsis') {", "if (rawKey === 'integral') {"),
    ("inverse", "if (rawKey === 'inverse') {", "if (rawKey === 'ellipsis') {"),
    ("sin", "if (rawKey === 'sin') {", "if (rawKey === 'cos') {"),
    ("cos", "if (rawKey === 'cos') {", "if (rawKey === 'tan') {"),
    ("tan", "if (rawKey === 'tan') {", "if (rawKey === 'scientific') {"),
    ("ans", "if (rawKey === 'ans') {", "if (rawKey === 'variable') {"),
    ("variable", "if (rawKey === 'variable') {", "if (rawKey === 'negate') {"),
    ("negate", "if (rawKey === 'negate') {", "if (rawKey === 's_to_d') {"),
    ("s_to_d", "if (rawKey === 's_to_d') {", "if (rawKey === 'm_plus') {"),
    ("m_plus", "if (rawKey === 'm_plus') {", "if (rawKey === 'optn') {"),
    ("right_paren", "if (rawKey === 'right_paren') {", "const tkMap = {"),
]

NODE_STUBS = """
const inserted = [];
function insertToken(t) { inserted.push(t); return true; }
function insertPower() { inserted.push('<power>'); return true; }
function handlePendingVar() { return false; }
function updateMemory() { inserted.push('<mem>'); return true; }
function toggleAnswerFormat() { inserted.push('<toggle>'); return true; }
function renderLCD() {}
function useAlphaForHex() { return false; }
const appState = { mode: 'Calculate', baseNBase: 10, variables: {} };
"""


def route_source():
    # Several `rawKey === 'negate'` / `'optn'` branches exist in the per-mode
    # handlers above the main key router. Anchor on the unique `rawKey ===
    # 'sto'` line so only the real routing block is sliced.
    anchor = FRONTEND.index("if (rawKey === 'sto') {")
    parts = []
    for _name, start_marker, end_marker in ROUTE_SLICES:
        start = FRONTEND.index(start_marker, anchor)
        end = FRONTEND.index(end_marker, start)
        parts.append(FRONTEND[start:end])
    return "\n".join(parts)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TestFrontendVariableRouting(unittest.TestCase):
    """5. Execute the real routing branches from frontend.html in node."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = PROJECT / ".x_variable_route_tmp.js"
        cls.tmp.write_text(
            NODE_STUBS
            + "function route(rawKey, isShift, isAlpha) {\n"
            + route_source() + "\nreturn inserted;\n}\n"
            + "const out=[];"
            + "for(const c of JSON.parse(process.argv[2])){"
            + "inserted.length=0;route(c.k,c.s,c.a);"
            + "out.push(inserted.slice());}"
            + "process.stdout.write(JSON.stringify(out));\n",
            encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.unlink(missing_ok=True)

    def _route(self, cases):
        proc = subprocess.run(
            ["node", str(self.tmp), json.dumps(cases)],
            capture_output=True, text=True, encoding="utf-8", timeout=60)
        assert proc.returncode == 0, proc.stderr[:500]
        return json.loads(proc.stdout)

    def test_x_key_inserts_uppercase_variable(self):
        # BUG-01: the unshifted `x` key must produce the X variable.
        self.assertEqual(self._route([{"k": "variable", "s": False, "a": False}]),
                         [["X"]])

    def test_alpha_right_paren_inserts_uppercase_variable(self):
        # BUG-01: ALPHA + `)` is the second route to the X variable.
        self.assertEqual(self._route([{"k": "right_paren", "s": False, "a": True}]),
                         [["X"]])

    def test_shift_x_key_still_inserts_sigma(self):
        # SHIFT on the same key must keep producing the summation template.
        out = self._route([{"k": "variable", "s": True, "a": False}])
        self.assertEqual(out, [["\u03a3("]])

    def test_plain_right_paren_unchanged(self):
        self.assertEqual(self._route([{"k": "right_paren", "s": False, "a": False}]),
                         [[")"]])

    def test_shift_right_paren_unchanged(self):
        self.assertEqual(self._route([{"k": "right_paren", "s": True, "a": True}]),
                         [[","]])

    def test_existing_alpha_variables_unchanged(self):
        # Every other ALPHA variable must still insert its uppercase letter.
        cases = [{"k": k, "s": False, "a": True} for k in
                 ("negate", "ellipsis", "inverse", "sin", "cos", "tan", "m_plus")]
        expected = [["A"], ["B"], ["C"], ["D"], ["E"], ["F"], ["M"]]
        self.assertEqual(self._route(cases), expected)

    def test_alpha_y_route_unchanged(self):
        # ALPHA on S<->D keeps its existing lowercase `y` token; the backend
        # alias is what makes it resolve to the Y variable.
        self.assertEqual(self._route([{"k": "s_to_d", "s": False, "a": True}]),
                         [["y"]])

    def test_no_route_inserts_bare_lowercase_x(self):
        # Guard: none of the variable keys may emit a bare lowercase `x`.
        cases = [{"k": k, "s": s, "a": a}
                 for k in ("variable", "right_paren", "negate", "ellipsis",
                           "inverse", "sin", "cos", "tan", "m_plus", "s_to_d")
                 for s in (False, True) for a in (False, True)]
        for case, tokens in zip(cases, self._route(cases)):
            for tok in tokens:
                self.assertNotEqual(
                    tok, "x",
                    f"{case} inserted a bare lowercase x")

    def test_solve_and_calc_still_wired(self):
        # BUG-02 path: SHIFT+CALC -> doSolve(), CALC -> doCalc().
        self.assertIn("doSolve(); return;", FRONTEND)
        self.assertIn("doCalc(); return;", FRONTEND)
        self.assertIn("'/api/solve'", FRONTEND)


class TestFrontendAlphaWiring(unittest.TestCase):
    """6. The `)` key's ALPHA label/attribute must name the X variable."""

    def _button(self, data_key):
        m = re.search(
            r"<button\b[^>]*data-key=\"" + re.escape(data_key) + r"\"[^>]*>",
            FRONTEND)
        assert m, f"button data-key={data_key!r} not found"
        return m.group(0)

    def test_right_paren_alpha_is_uppercase_x(self):
        btn = self._button("right_paren")
        self.assertIn('data-alpha="X"', btn)
        self.assertNotIn('data-alpha="x"', btn)

    def test_right_paren_alpha_label_reads_x(self):
        # The printed ALPHA legend must match what the key actually inserts.
        m = re.search(
            r'<span class="lbl"><span class="alpha-mark">([^<]+)</span></span>'
            r'<button class="b" data-shift="comma" data-alpha="X" '
            r'data-key="right_paren">', FRONTEND)
        assert m, "right_paren ALPHA legend not found"
        self.assertEqual(m.group(1), "X")

    def test_variable_key_present(self):
        self.assertIn('data-shift="Sigma" data-key="variable"', FRONTEND)

    def test_all_nine_variables_reachable_from_alpha_buttons(self):
        alpha = set(re.findall(r'data-alpha="([A-Za-z])"', FRONTEND))
        for name in "ABCDEF":
            self.assertIn(name, alpha, name)
        self.assertIn("M", alpha)
        self.assertIn("X", alpha)


# Small math helpers so the expected values are not re-derived by hand.
def math_sqrt(v):
    import math
    return math.sqrt(v)


def math_log(v):
    import math
    return math.log(v)


def math_e_pow(v):
    import math
    return math.e ** v


if __name__ == "__main__":
    unittest.main()
