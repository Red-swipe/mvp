"""Parity regression matrix for the fx-991EX implementation pass.

Covers the minimum regression matrix from the task spec:
core arithmetic, SHIFT functions, ALPHA variables, advanced math
(sigma/diff/integral), STO/RECALL/CALC/SOLVE, equations, inequalities,
Base-N, error contract (1/0 custom message), and frontend button wiring.
"""
import math
import pathlib
import unittest

from mvp_server import (
    DIV_ZERO_MSG,
    CalculatorController,
    evaluate_base_n,
    safe_evaluate_expression,
)

VARS = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0,
        "F": 0.0, "M": 0.0, "X": 0.0, "Y": 0.0}


def ev(expr, variables=None, angle="Degree", ans=0.0):
    return safe_evaluate_expression(expr, ans, angle,
                                    dict(variables if variables is not None else VARS))


class TestCore(unittest.TestCase):
    def test_core_matrix(self):
        self.assertAlmostEqual(ev("1+1"), 2.0)
        self.assertAlmostEqual(ev("2*3"), 6.0)
        self.assertAlmostEqual(ev("10/2"), 5.0)
        self.assertAlmostEqual(ev("2^2"), 4.0)
        self.assertAlmostEqual(ev("sqrt(9)"), 3.0)
        self.assertAlmostEqual(ev("sin(30)"), 0.5)
        self.assertAlmostEqual(ev("log(100)"), 2.0)
        self.assertAlmostEqual(ev("ln(e)"), 1.0)


class TestShiftFunctions(unittest.TestCase):
    def test_percent(self):
        self.assertAlmostEqual(ev("50%"), 0.5)
        self.assertAlmostEqual(ev("200+10%"), 200.1, places=6)

    def test_factorial(self):
        self.assertAlmostEqual(ev("5!"), 120.0)
        self.assertEqual(ev("FACT(12)"), "2^2×3")
        self.assertEqual(ev("FACT(13)"), "13")

    def test_round_alias(self):
        self.assertAlmostEqual(ev("Rnd(2.5)"), 2.0)
        self.assertAlmostEqual(ev("round(2.5)"), 2.0)

    def test_random(self):
        r = ev("Ran#")
        self.assertTrue(0.0 <= r < 1.0)
        self.assertEqual(ev("RanInt(1,1)"), 1)
        r2 = ev("RanInt(1,6)")
        self.assertTrue(1 <= r2 <= 6)

    def test_pol_rec(self):
        self.assertAlmostEqual(ev("Pol(2,2)"), math.hypot(2, 2))
        self.assertAlmostEqual(ev("Rec(2,45)"), math.sqrt(2))

    def test_combinatorics(self):
        self.assertEqual(ev("5P2"), 20)
        self.assertEqual(ev("5C2"), 10)

    def test_powers(self):
        self.assertAlmostEqual(ev("10^(2)"), 100.0)
        self.assertAlmostEqual(ev("e^(1)"), math.e)
        self.assertAlmostEqual(ev("(2)^(3)"), 8.0)
        self.assertAlmostEqual(ev("cbrt(27)"), 3.0)
        self.assertAlmostEqual(ev("xroot(3,8)"), 2.0)
        self.assertAlmostEqual(ev("Abs(0-7)"), 7.0)


class TestAlphaVariables(unittest.TestCase):
    def test_variable_eval(self):
        self.assertAlmostEqual(ev("A*2", {**VARS, "A": 5}), 10.0)
        self.assertAlmostEqual(ev("X+Y", {**VARS, "X": 3, "Y": 4}), 7.0)

    def test_complex_i(self):
        r = ev("i", VARS)
        self.assertTrue(isinstance(r, complex))

    def test_colon_separator(self):
        self.assertAlmostEqual(ev("2+2:3*3"), 9.0)


class TestAdvancedMath(unittest.TestCase):
    def test_sigma(self):
        self.assertAlmostEqual(ev("sigma(x,1,5)"), 15.0)
        self.assertAlmostEqual(ev("Σ(x,1,5)"), 15.0)

    def test_diff(self):
        self.assertAlmostEqual(ev("diff(x^2,3)"), 6.0, places=3)
        self.assertAlmostEqual(ev("d/dx(x^2,3)"), 6.0, places=3)

    def test_integral(self):
        self.assertAlmostEqual(ev("integral(x^2,0,1)"), 1 / 3, places=3)
        self.assertAlmostEqual(ev("integral(ln(x),1,e)"), 1.0, places=3)


class TestVariablesCalcSolve(unittest.TestCase):
    def setUp(self):
        self.ctrl = CalculatorController()

    def test_sto_recall(self):
        r = self.ctrl.set_variable("A", 7)
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(
            safe_evaluate_expression("A*2", 0.0, "Degree", self.ctrl.variables), 14.0)
        bad = self.ctrl.set_variable("Z", 1)
        self.assertFalse(bad["ok"])

    def test_reset_clears_variables(self):
        self.ctrl.set_variable("A", 9)
        self.ctrl.reset_calculator("all")
        self.assertEqual(self.ctrl.variables["A"], 0.0)

    def test_calc(self):
        r = self.ctrl.calc_evaluate("A*2+1", {"A": 5})
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"], "11")

    def test_solve_quadratic(self):
        r = self.ctrl.solve_equation_newton("X^2-4", "X", 1.0)
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(float(r["result"]), 2.0, places=5)

    def test_solve_with_equals(self):
        r = self.ctrl.solve_equation_newton("X^2=4", "X", 1.0)
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(float(r["result"]), 2.0, places=5)

    def test_solve_failure(self):
        r = self.ctrl.solve_equation_newton("X^2+1", "X", 0.0)
        self.assertFalse(r["ok"])


class TestEquations(unittest.TestCase):
    def setUp(self):
        self.ctrl = CalculatorController()

    def test_quadratic(self):
        r = self.ctrl.solve_equation("polynomial", [1, 5, 6], 2)
        self.assertTrue(r["ok"])

    def test_cubic(self):
        r = self.ctrl.solve_equation("polynomial", [1, 0, 0, 0], 3)
        self.assertTrue(r["ok"])

    def test_simultaneous_2x2(self):
        r = self.ctrl.solve_equation("simultaneous", [[1, 1, 3], [1, -1, 1]], 2)
        self.assertTrue(r["ok"])

    def test_simultaneous_3x3(self):
        r = self.ctrl.solve_equation(
            "simultaneous",
            [[1, 0, 0, 1], [0, 1, 0, 2], [0, 0, 1, 3]], 3)
        self.assertTrue(r["ok"])


class TestInequalities(unittest.TestCase):
    def setUp(self):
        self.ctrl = CalculatorController()

    def test_all_degrees_operators(self):
        coeffs = {2: [1, 0, -1], 3: [1, 0, 0, 0], 4: [1, 0, 0, 0, 0]}
        for degree, c in coeffs.items():
            for op in (">", "<", "≥", "≤"):
                with self.subTest(degree=degree, op=op):
                    r = self.ctrl.solve_inequality(degree, op, c)
                    self.assertTrue(r["ok"], f"degree={degree} op={op}: {r}")


class TestBaseN(unittest.TestCase):
    def test_all_bases(self):
        self.assertEqual(evaluate_base_n("1010+1", 2), "1011")
        self.assertEqual(evaluate_base_n("17+1", 8), "20")
        self.assertEqual(evaluate_base_n("9+1", 10), "10")
        self.assertEqual(evaluate_base_n("A+1", 16), "B")
        self.assertEqual(evaluate_base_n("FF", 16), "FF")

    def test_controller_base_switch_needs_shift(self):
        c = CalculatorController()
        c.set_mode("Base-N", "3")
        c.shift = False
        tok = c._token_for("square")
        self.assertNotIn("BASE_SWITCH", tok)
        c.shift = True
        tok2 = c._token_for("square")
        self.assertIn("BASE_SWITCH", tok2)


class TestErrorContract(unittest.TestCase):
    def test_div_zero_message(self):
        c = CalculatorController()
        c.expression = "1/0"
        st = c.press_key({"key": "equals", "expression": "1/0"})
        self.assertEqual(st["display"], DIV_ZERO_MSG)
        self.assertIn("beyonddd", DIV_ZERO_MSG)

    def test_math_error_not_leaked(self):
        with self.assertRaises(ValueError) as ctx:
            ev("sqrt(0-1)")
        self.assertIn("Math ERROR", str(ctx.exception))
        self.assertNotIn("Traceback", str(ctx.exception))


class TestFrontendWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = pathlib.Path("frontend.html").read_text(encoding="utf-8")

    def test_swapped_mappings_fixed(self):
        self.assertIn('data-shift="d/dx" data-alpha=":" data-key="integral"', self.html)
        self.assertIn('data-shift="Sigma" data-key="variable"', self.html)
        self.assertIn("if (isAlpha) { insertToken(':'); return; }", self.html)
        self.assertIn("insertToken(isShift ? '\\u03a3(' : 'x'); return;", self.html)

    def test_percent_comma_fact_wiring(self):
        self.assertIn('data-shift="percent" data-key="ans"', self.html)
        self.assertIn('data-shift="comma"', self.html)
        self.assertIn("insertToken('FACT('); return;", self.html)
        self.assertIn("insertToken('%'); return;", self.html)
        self.assertIn("insertToken(','); return;", self.html)

    def test_del_labels(self):
        self.assertIn('data-shift="INS" data-alpha="UNDO" data-key="del"', self.html)

    def test_eng_alpha_i(self):
        self.assertIn('data-alpha="i" data-key="eng"', self.html)
        self.assertIn("insertToken('i'); return;", self.html)

    def test_calc_solve_sto(self):
        self.assertIn("rawKey === 'sto'", self.html)
        self.assertIn("rawKey === 'calc'", self.html)
        self.assertIn("doSolve(); return;", self.html)
        self.assertIn("doCalc(); return;", self.html)
        self.assertIn("storeVariable", self.html)

    def test_qr_in_lcd(self):
        self.assertIn('id="qr-panel"', self.html)
        self.assertIn("showQRinLCD", self.html)
        self.assertNotIn("window.open('https://mentisai-delta.vercel.app/'", self.html)

    def test_mixed_fraction(self):
        self.assertIn("insertMixedFraction", self.html)
        self.assertIn("type === 'mixed'", self.html)

    def test_katex_mappings(self):
        self.assertIn("sum_{", self.html)
        self.assertIn("frac{d}{dx}", self.html)


if __name__ == "__main__":
    unittest.main()
