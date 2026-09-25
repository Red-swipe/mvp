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
        # Norm: 10 significant digits -> values are (almost) unchanged
        self.assertAlmostEqual(ev("Rnd(2.5)"), 2.5)
        self.assertAlmostEqual(ev("round(2.5)"), 2.5)
        self.assertAlmostEqual(ev("Rnd(1/3)"), 0.3333333333)

    def test_rnd_fix(self):
        from mvp_server import safe_evaluate_expression as see
        # Fix 3: Rnd(10/3) == 3.333 internal and displayed (manual example)
        self.assertAlmostEqual(
            see("Rnd(10/3)", 0.0, "Degree", dict(VARS), False, ("Fix", 3)), 3.333)
        self.assertAlmostEqual(
            see("Rnd(2.3455)", 0.0, "Degree", dict(VARS), False, ("Fix", 3)), 2.346)
        self.assertAlmostEqual(
            see("Rnd(0-2.3455)", 0.0, "Degree", dict(VARS), False, ("Fix", 3)), -2.346)
        self.assertAlmostEqual(
            see("Rnd(2.5)", 0.0, "Degree", dict(VARS), False, ("Fix", 0)), 3.0)

    def test_rnd_sci_norm(self):
        from mvp_server import safe_evaluate_expression as see
        # Sci 5: 5 significant digits
        self.assertAlmostEqual(
            see("Rnd(123.456789)", 0.0, "Degree", dict(VARS), False, ("Sci", 5)), 123.46)
        # Norm: 10 significant digits
        self.assertAlmostEqual(
            see("Rnd(10/3)", 0.0, "Degree", dict(VARS), False, ("Norm",)), 3.333333333,
            places=9)
        # Rnd result feeds further arithmetic (manual: Rnd(10/3)*3 == 9.999 Fix 3)
        self.assertAlmostEqual(
            see("Rnd(10/3)*3", 0.0, "Degree", dict(VARS), False, ("Fix", 3)), 9.999)

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


class TestMatrixVector(unittest.TestCase):
    def setUp(self):
        self.ctrl = CalculatorController()
        self.ctrl.set_matrix("A", 2, 2, [[1, 2], [3, 4]])
        self.ctrl.set_matrix("B", 2, 2, [[5, 6], [7, 8]])
        self.ctrl.set_vector("A", 3, [1, 2, 2])
        self.ctrl.set_vector("B", 3, [1, 0, 0])

    def eq(self, expr):
        return self.ctrl.press_key({"key": "equals", "expression": expr})

    def test_matrix_add_sub(self):
        self.assertEqual(self.eq("MatA+MatB")["result"], "[[6,8],[10,12]]")
        self.assertEqual(self.eq("MatA-MatB")["result"], "[[-4,-4],[-4,-4]]")

    def test_matrix_answer_keeps_scalar_ans(self):
        self.eq("2+3")
        self.assertEqual(self.ctrl.ans, "5")
        self.eq("MatA+MatB")
        self.assertEqual(self.ctrl.ans, "5")
        self.assertEqual(self.ctrl.ans_matrix, "[[6,8],[10,12]]")
        self.assertEqual(self.eq("Ans+1")["result"], "6")

    def test_matrix_multiply(self):
        self.assertEqual(self.eq("MatA*MatB")["result"], "[[19,22],[43,50]]")

    def test_matrix_scalar(self):
        self.assertEqual(self.eq("2*MatA")["result"], "[[2,4],[6,8]]")
        self.assertEqual(self.eq("MatA*3")["result"], "[[3,6],[9,12]]")

    def test_matrix_det_transpose(self):
        self.assertEqual(self.eq("Det(MatA)")["result"], "-2")
        self.assertEqual(self.eq("Trn(MatA)")["result"], "[[1,3],[2,4]]")

    def test_matrix_inverse_power(self):
        r = self.eq("MatA^(-1)")
        self.assertTrue(r["ok"])
        inv = [[float(x) for x in row.strip("[]").split(",")]
               for row in r["result"].strip("[]").split("],[")]
        self.assertAlmostEqual(inv[0][0], -2.0)
        self.assertAlmostEqual(inv[1][1], -0.5)
        self.assertEqual(self.eq("MatA^2")["result"], "[[7,10],[15,22]]")

    def test_matrix_identity_abs(self):
        self.assertEqual(self.eq("Identity(2)")["result"], "[[1,0],[0,1]]")
        self.ctrl.set_matrix("C", 2, 2, [[-1, 2], [3, -4]])
        self.assertEqual(self.eq("Abs(MatC)")["result"], "[[1,2],[3,4]]")

    def test_matrix_endpoints(self):
        self.assertEqual(
            self.ctrl.calculate_matrix("multiply", "A", "B")["result"],
            "[[19,22],[43,50]]")
        self.assertEqual(
            self.ctrl.calculate_matrix("determinant", "A")["result"], "-2")

    def test_matrix_errors(self):
        self.ctrl.set_matrix("C", 3, 3, [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        r = self.eq("MatA+MatC")
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "Dimension ERROR")
        r = self.eq("Det(MatC)")
        self.assertTrue(r["ok"])  # square: fine
        self.ctrl.set_matrix("D", 2, 3, [[1, 2, 3], [4, 5, 6]])
        r = self.eq("Det(MatD)")
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "Dimension ERROR")
        self.ctrl.set_matrix("D", 2, 2, [[1, 2], [2, 4]])  # singular
        r = self.eq("MatD^(-1)")
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "Math ERROR")
        r = self.eq("MatC+MatD")  # 3x3 vs 2x2
        self.assertEqual(r["error"], "Dimension ERROR")

    def test_vector_ops(self):
        self.assertEqual(self.eq("VctA+VctB")["result"], "[2,2,2]")
        self.assertEqual(self.eq("VctA-VctB")["result"], "[0,2,2]")
        self.assertEqual(self.eq("2*VctA")["result"], "[2,4,4]")
        self.assertEqual(self.eq("Dot(VctA,VctB)")["result"], "1")
        self.assertEqual(self.eq("VctA*VctB")["result"], "[0,2,-2]")
        self.assertEqual(self.eq("Abs(VctA)")["result"], "3")

    def test_vector_angle_unit(self):
        r = self.eq("Angle(VctA,VctB)")
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(float(r["result"]), 70.52877937, places=5)
        self.assertEqual(
            self.ctrl.calculate_vector("dot", "A", "B")["result"], "1")

    def test_vector_errors(self):
        self.ctrl.set_vector("C", 2, [1, 0])
        r = self.eq("VctA+VctC")
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "Dimension ERROR")
        r = self.eq("VctA*VctC")  # cross needs 3-D
        self.assertEqual(r["error"], "Dimension ERROR")


class TestDisplayLayer(unittest.TestCase):
    def test_decimal_mark_dot(self):
        from mvp_server import format_display
        self.assertEqual(format_display("1.5", "Dot", False), "1.5")
        self.assertEqual(format_display("[[1.5,2]]", "Dot", False), "[[1.5,2]]")

    def test_decimal_mark_comma(self):
        from mvp_server import format_display
        self.assertEqual(format_display("1.5", "Comma", False), "1,5")
        self.assertEqual(format_display("-2.25", "Comma", False), "-2,25")
        # multi-value separators become semicolons (manual)
        self.assertEqual(format_display("[[1.5,2]]", "Comma", False), "[[1,5;2]]")
        self.assertEqual(format_display("[1.5,2]", "Comma", False), "[1,5;2]")
        self.assertEqual(format_display("1.234×10^3", "Comma", False), "1,234×10^3")
        # errors pass through untouched
        self.assertEqual(format_display("Math ERROR", "Comma", True), "Math ERROR")

    def test_digit_separator(self):
        from mvp_server import format_display
        self.assertEqual(format_display("1234567", "Dot", True), "1 234 567")
        self.assertEqual(format_display("1234.5", "Dot", True), "1 234.5")
        self.assertEqual(format_display("123", "Dot", True), "123")
        self.assertEqual(format_display("-1234567", "Dot", True), "-1 234 567")
        # combined with comma mark
        self.assertEqual(format_display("1234567.89", "Comma", True), "1 234 567,89")

    def test_display_does_not_leak_into_eval(self):
        from mvp_server import safe_evaluate_expression
        c = CalculatorController()
        c.setup_settings["decimal_mark"] = "Comma"
        c.setup_settings["digit_separator"] = True
        st = c.press_key({"key": "equals", "expression": "1234567+0.5"})
        self.assertTrue(st["ok"])
        self.assertEqual(st["display"], "1 234 567,5")
        # canonical result stays evaluable; Ans reuse is unaffected
        self.assertEqual(st["result"], "1234567.5")
        st2 = c.press_key({"key": "equals", "expression": "Ans+1"})
        self.assertEqual(st2["result"], "1234568.5")


class TestComplexParity(unittest.TestCase):
    CM = True
    RE = False

    def test_real_mode_rejects(self):
        for expr in ("i*i", "sqrt(0-1)", "asin(2)", "ln(0-1)", "sin(i)"):
            if expr == "i*i":
                self.assertAlmostEqual(ev(expr, VARS, "Degree", 0.0), -1.0)
                continue
            with self.assertRaises(ValueError, msg=expr):
                safe_evaluate_expression(expr, 0.0, "Degree", dict(VARS))

    def test_complex_arithmetic(self):
        self.assertAlmostEqual(
            safe_evaluate_expression("i*i", 0.0, "Degree", dict(VARS), True), -1.0)
        r = safe_evaluate_expression("(1+i)^2", 0.0, "Degree", dict(VARS), True)
        self.assertTrue(isinstance(r, complex))
        self.assertAlmostEqual(r.imag, 2.0)
        self.assertAlmostEqual(
            safe_evaluate_expression("Abs(3+4*i)", 0.0, "Degree", dict(VARS), True), 5.0)

    def test_complex_sqrt_asin(self):
        r = safe_evaluate_expression("sqrt(0-1)", 0.0, "Degree", dict(VARS), True)
        self.assertAlmostEqual(r.imag, 1.0)
        r = safe_evaluate_expression("asin(2)", 0.0, "Degree", dict(VARS), True)
        self.assertAlmostEqual(r.real, 90.0, places=5)
        # deterministic explicit-formula branch (matches FILE_MODE bridge)
        self.assertAlmostEqual(r.imag, -75.45612929, places=5)

    def test_power_negation_precedence(self):
        # fx-991EX priority: powers bind tighter than a leading minus.
        self.assertAlmostEqual(ev("-2^2"), -4.0)
        self.assertAlmostEqual(ev("(-2)^2"), 4.0)
        self.assertAlmostEqual(ev("2^-2"), 0.25)

    def test_complex_ln_trig(self):
        r = safe_evaluate_expression("ln(0-1)", 0.0, "Degree", dict(VARS), True)
        self.assertAlmostEqual(r.imag, math.pi, places=6)
        r = safe_evaluate_expression("sin(i)", 0.0, "Degree", dict(VARS), True)
        # sin(i * pi/180) = i * sinh(pi/180)
        self.assertAlmostEqual(r.imag, math.sinh(math.pi / 180), places=9)
        self.assertAlmostEqual(r.real, 0.0, places=9)

    def test_complex_mode_controller(self):
        c = CalculatorController()
        c.set_mode("Complex", "2")
        r = c.press_key({"key": "equals", "expression": "sqrt(0-1)"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"], "1i")

    def test_calculate_rejects_complex(self):
        c = CalculatorController()
        r = c.press_key({"key": "equals", "expression": "(1+i)^2"})
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "Math ERROR")
        # ...but real-valued complex arithmetic still works there
        r = c.press_key({"key": "equals", "expression": "i*i"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"], "-1")

    def test_real_odd_roots(self):
        self.assertAlmostEqual(ev("cbrt(0-8)"), -2.0)
        self.assertAlmostEqual(ev("xroot(3,0-8)"), -2.0)


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

    def test_matrix_vector_ui(self):
        self.assertIn('id="optn-mat-menu"', self.html)
        self.assertIn('id="optn-vct-menu"', self.html)
        self.assertIn("insertOptn('MatA')", self.html)
        self.assertIn("insertOptn('Det(')", self.html)
        self.assertIn("insertOptn('VctA')", self.html)
        self.assertIn("insertOptn('Dot(')", self.html)
        self.assertIn("insertOptn('Angle(')", self.html)
        self.assertIn("insertOptn('UnitV(')", self.html)
        self.assertIn("insertOptn('Identity(')", self.html)
        self.assertIn("insertOptn('Trn(')", self.html)
        self.assertIn("Mat CALC", self.html)
        self.assertIn("Vct CALC", self.html)
        self.assertIn("minp.phase = 'calc'", self.html)
        self.assertIn("vi.phase = 'calc'", self.html)
        self.assertIn("begin{bmatrix}", self.html)

    def test_dpad_center_wiring(self):
        self.assertIn("if (rawKey === 'dpad_center') return;", self.html)
        self.assertIn("rawKey === 'dpad_center') {", self.html)

    def test_display_format_wiring(self):
        self.assertIn("function displayFormat(canonical)", self.html)
        self.assertIn("displayFormat(appState.result)", self.html)
        self.assertIn("displayFormat(r.result)", self.html)
        self.assertIn("displayFormat(di.result)", self.html)
        self.assertIn("displayFormat(row.value)", self.html)


if __name__ == "__main__":
    unittest.main()
