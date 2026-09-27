"""Regression tests for BUG-08: contextual percentage semantics.

``%`` used to be rewritten as a bare ``operand/100`` with no knowledge of what
preceded it, so ``100+10%`` evaluated to 100.1. A Casio-style calculator reads
``%`` as *of the value on its left*, so ``100+10%`` is 100 + 100*10/100 = 110.

The rule now implemented in ``_transform_percent``:
  * after ``+`` or ``-`` -> base is the value to the left  (100+10% = 110)
  * after ``*`` or ``/``, or standalone -> plain scale       (100*10% = 10)

Everything here goes through ``safe_evaluate_expression``, the same evaluation
boundary the rest of the backend suite uses; the frontend keeps emitting a bare
``%`` token and is not involved.
"""
import unittest

from mvp_server import (
    CalculatorController,
    _percent_base,
    _PERCENT_RE,
    safe_evaluate_expression,
)

VARS = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0,
        "F": 0.0, "M": 0.0, "X": 0.0, "Y": 0.0}


def ev(expr, ans=0.0, variables=None, angle="Degree"):
    return safe_evaluate_expression(
        expr, ans, angle, dict(VARS if variables is None else variables))


class TestPercentStandalone(unittest.TestCase):
    """1. Standalone percentages are still a plain scale."""

    def test_standalone(self):
        self.assertAlmostEqual(ev("10%"), 0.1)
        self.assertAlmostEqual(ev("50%"), 0.5)
        self.assertAlmostEqual(ev("200%"), 2.0)
        self.assertAlmostEqual(ev("0%"), 0.0)
        self.assertAlmostEqual(ev("0.5%"), 0.005)

    def test_parenthesised_operand(self):
        self.assertAlmostEqual(ev("(3+7)%"), 0.1)

    def test_negative_percent_has_no_left_operand(self):
        # '-10%' starts the expression, so the sign is unary: no base exists.
        self.assertAlmostEqual(ev("-10%"), -0.1)


class TestPercentContextualArithmetic(unittest.TestCase):
    """2-6. The four operator contexts, decimals and zero."""

    def test_addition(self):
        self.assertAlmostEqual(ev("100+10%"), 110.0)
        self.assertAlmostEqual(ev("200+5%"), 210.0)
        self.assertAlmostEqual(ev("80+12.5%"), 90.0)

    def test_subtraction(self):
        self.assertAlmostEqual(ev("100-10%"), 90.0)
        self.assertAlmostEqual(ev("200-5%"), 190.0)

    def test_multiplication_keeps_plain_scale(self):
        self.assertAlmostEqual(ev("100*10%"), 10.0)
        self.assertAlmostEqual(ev("50*20%"), 10.0)
        self.assertAlmostEqual(ev("200*5%"), 10.0)

    def test_division_keeps_plain_scale(self):
        self.assertAlmostEqual(ev("100/10%"), 1000.0)
        self.assertAlmostEqual(ev("50/20%"), 250.0)
        self.assertAlmostEqual(ev("200/5%"), 4000.0)

    def test_decimal_percentages(self):
        self.assertAlmostEqual(ev("80+12.5%"), 90.0)
        self.assertAlmostEqual(ev("3.5+2.5%"), 3.5875)

    def test_zero_base(self):
        self.assertAlmostEqual(ev("0+10%"), 0.0)
        self.assertAlmostEqual(ev("0-10%"), 0.0)

    def test_negative_left_value(self):
        self.assertAlmostEqual(ev("-(100)+10%"), -110.0)


class TestPercentBaseSelection(unittest.TestCase):
    """The base is the maximal value to the left, not just a bare number."""

    def test_parenthesised_base(self):
        self.assertAlmostEqual(ev("(3+7)+10%"), 11.0)

    def test_product_base(self):
        self.assertAlmostEqual(ev("(2+3)*4+10%"), 22.0)

    def test_power_base(self):
        self.assertAlmostEqual(ev("2^2+10%"), 4.4)

    def test_additive_run_base(self):
        # The value immediately left of the last '+' is 26.
        self.assertAlmostEqual(ev("2*3+4*5+10%"), 28.6)

    def test_base_inside_parens_is_standalone(self):
        # The % sits one level deeper, so it has no left operand at its depth.
        self.assertAlmostEqual(ev("2+(10%)"), 2.1)
        self.assertAlmostEqual(ev("2*(10%)"), 0.2)

    def test_paren_group_does_not_leak_outward(self):
        # Regression: the base scan once walked through an unmatched '(' and
        # produced unbalanced output for 100*(1+10%).
        self.assertAlmostEqual(ev("100*(1+10%)"), 110.0)

    def test_nested_call_base(self):
        self.assertAlmostEqual(ev("1+(2+3)+10%"), 6.6)

    def test_percent_then_multiplication(self):
        # The % binds tightest; 10% of 100 is 10, doubled.
        self.assertAlmostEqual(ev("100+10%*2"), 120.0)
        self.assertAlmostEqual(ev("100*(1+10%)"), 110.0)


class TestPercentFunctionAndVariableBases(unittest.TestCase):
    """A function call, variable or Ans to the left is a valid base."""

    def test_function_bases(self):
        self.assertAlmostEqual(ev("sqrt(4)+10%"), 2.2)
        self.assertAlmostEqual(ev("log(100)+10%"), 2.2)
        self.assertAlmostEqual(ev("xroot(3,8)+10%"), 2.2)
        self.assertAlmostEqual(ev("round(2.5)+10%"), 2.75)
        self.assertAlmostEqual(ev("Rnd(2.5)+10%"), 2.75)

    def test_two_argument_function_base(self):
        # Regression: the base scan truncated identifiers that were not 'e',
        # turning log_base(2,8)+10% into the invalid "e(2,8)".
        self.assertAlmostEqual(ev("log_base(2,8)+10%"), 3.3)

    def test_function_base_with_subtraction(self):
        self.assertAlmostEqual(ev("sqrt(4)-10%"), 1.8)
        self.assertAlmostEqual(ev("log(100)-10%"), 1.8)

    def test_variable_base(self):
        self.assertAlmostEqual(ev("A+10%", variables={**VARS, "A": 5.0}), 5.5)
        self.assertAlmostEqual(ev("A-10%", variables={**VARS, "A": 5.0}), 4.5)
        self.assertAlmostEqual(ev("A*10%", variables={**VARS, "A": 5.0}), 0.5)

    def test_ans_base(self):
        # Ans is substituted before _transform_percent runs, so the base is its
        # numeric value rather than the literal name.
        self.assertAlmostEqual(ev("Ans+10%", ans=5.0), 5.5)
        self.assertAlmostEqual(ev("Ans-10%", ans=5.0), 4.5)
        self.assertAlmostEqual(ev("Ans*10%", ans=5.0), 0.5)


class TestPercentChains(unittest.TestCase):
    """9. Chained percentages: each '%' uses the already-expanded value."""

    def test_additive_chain(self):
        # 100+10% = 110, then +5% of 110 = 115.5
        self.assertAlmostEqual(ev("100+10%+5%"), 115.5)

    def test_subtractive_chain(self):
        # 100-10% = 90, then -5% of 90 = 85.5
        self.assertAlmostEqual(ev("100-10%-5%"), 85.5)

    def test_short_subtractive_chain(self):
        # 50-10% = 45, then -5% of 45 = 42.75
        self.assertAlmostEqual(ev("50-10%-5%"), 42.75)

    def test_chain_then_scalar(self):
        self.assertAlmostEqual(ev("100+10%*2"), 120.0)


class TestPercentErrorContract(unittest.TestCase):
    """Malformed input keeps the calculator's normal Math ERROR contract."""

    def assertMathError(self, expr):
        with self.assertRaises(ValueError, msg=expr):
            ev(expr)

    def test_bare_percent(self):
        self.assertMathError("%")

    def test_double_percent(self):
        self.assertMathError("10%%")

    def test_empty_group_percent(self):
        self.assertMathError("()%")

    def test_trailing_percent_expression(self):
        self.assertMathError("10%10%")

    def test_undefined_name_with_percent(self):
        self.assertMathError("zz+10%")

    def test_no_python_exception_leaks(self):
        for expr in ("%", "()%", "10%%", "2e+10%"):
            try:
                ev(expr)
            except ValueError:
                pass                      # the calculator's own error type
            except Exception as exc:      # pragma: no cover
                self.fail(f"{expr} leaked {type(exc).__name__}: {exc}")


class TestPercentBaseHelper(unittest.TestCase):
    """Unit-level checks on the base scanner, without a full evaluation."""

    def _base(self, expr):
        depth = [0] * (len(expr) + 1)
        level = 0
        for i, ch in enumerate(expr):
            depth[i] = level
            if ch == "(":
                level += 1
            elif ch == ")":
                level -= 1
        m = _PERCENT_RE.search(expr)
        assert m, expr
        return _percent_base(expr, m.start(), depth)

    def test_additive_context_yields_left_value(self):
        self.assertEqual(self._base("100+10%"), "100")
        self.assertEqual(self._base("sqrt(4)+10%"), "sqrt(4)")
        self.assertEqual(self._base("log_base(2,8)+10%"), "log_base(2,8)")
        self.assertEqual(self._base("(2+3)*4+10%"), "(2+3)*4")

    def test_non_additive_contexts_yield_none(self):
        for expr in ("100*10%", "100/10%", "10%", "-10%", "2+(10%)"):
            self.assertIsNone(self._base(expr), expr)


class TestPercentRegression(unittest.TestCase):
    """10. Everything without a '%' is untouched."""

    def test_plain_arithmetic(self):
        self.assertAlmostEqual(ev("1+2"), 3.0)
        self.assertAlmostEqual(ev("10/2"), 5.0)
        self.assertAlmostEqual(ev("3.5*2"), 7.0)
        self.assertAlmostEqual(ev("2^10"), 1024.0)

    def test_other_shift_functions(self):
        self.assertAlmostEqual(ev("5!"), 120.0)
        self.assertAlmostEqual(ev("sin(30)"), 0.5)
        self.assertAlmostEqual(ev("log(100)"), 2.0)
        self.assertAlmostEqual(ev("ln(e)"), 1.0)
        self.assertAlmostEqual(ev("50%"), 0.5)
        self.assertAlmostEqual(ev("200+10%"), 220.0)

    def test_controller_path_agrees(self):
        # The route the frontend actually calls.
        ctrl = CalculatorController()
        for expr, want in (("100+10%", 110.0), ("100-10%", 90.0),
                           ("100*10%", 10.0), ("10%", 0.1)):
            out = ctrl.press_key({"key": "equals", "expression": expr})
            self.assertTrue(out.get("ok"), out)
            self.assertAlmostEqual(float(out.get("result")), want, msg=expr)


if __name__ == "__main__":
    unittest.main()
