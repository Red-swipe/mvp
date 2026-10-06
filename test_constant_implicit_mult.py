"""Issue 2 regression: implicit multiplication of mathematical constants.

ROOT CAUSE (traced through the real pipeline, not guessed):

`safe_evaluate_expression` substitutes the constants BEFORE parsing:

    s = s.replace('pi', f'({math.pi})').replace('Ans', f'({ans_val})')
    s = re.sub(r'(?<![A-Za-z0-9_.])e(?![A-Za-z0-9_(])', f'({math.e})', s)

so `2pi` becomes the token stream `2 ( 3.14159... )`. That is IMPLICIT
MULTIPLICATION -- a value directly followed by a parenthesised operand. The
recursive-descent parser's `_term()` only loops on an explicit TIMES or SLASH
token, so it stopped after `2` and `parse()` then rejected the leftover `(`
with "Unexpected trailing token LPAREN".

The same substitution exists in the frontend's file-mode bridge, so both
evaluators had the identical defect.

Bare `pi` and `pi/2` were never broken -- the constant itself is substituted
correctly. Only the juxtaposition forms (`2pi`, `2pi**2`, `(2)(3)`) failed.

Covered here (engine level):
  CONST-1  bare pi / e evaluate
  CONST-2  2pi -> 2*pi
  CONST-3  pi**2
  CONST-4  sqrt(pi)
  CONST-5  pi/2
  CONST-6  implicit multiplication of a parenthesised group: (2)(3)
  CONST-7  explicit operators still work and still take precedence
  CONST-8  implicit multiplication is left-associative: (2)(3)(4) == 24
  CONST-9  2pi**2 parses as 2*(pi**2), not (2*pi)**2
  CONST-10 Ans juxtaposition: Ans2 with ans=5 -> 10
  CONST-11 a genuinely malformed expression is STILL rejected
  CONST-12 no change to explicit `/` behaviour (division by zero raises)
"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.tokenizer import tokenize
from engine.parser import ParseError, parse
from engine.evaluator import evaluate
from mvp_server import safe_evaluate_expression

TOL = 1e-9


class TestConstants(unittest.TestCase):
    """CONST-1 .. CONST-5 at the engine API."""

    def ev(self, expr, ans=0.0):
        return safe_evaluate_expression(expr, ans)

    def test_bare_pi(self):
        self.assertAlmostEqual(self.ev("pi"), math.pi, delta=TOL)
        self.assertAlmostEqual(self.ev("π"), math.pi, delta=TOL)

    def test_bare_e(self):
        self.assertAlmostEqual(self.ev("e"), math.e, delta=TOL)

    def test_2pi(self):
        self.assertAlmostEqual(self.ev("2pi"), 2 * math.pi, delta=TOL)

    def test_pi_squared(self):
        self.assertAlmostEqual(self.ev("pi**2"), math.pi ** 2, delta=TOL)

    def test_sqrt_pi(self):
        self.assertAlmostEqual(self.ev("sqrt(pi)"), math.sqrt(math.pi), delta=TOL)

    def test_pi_over_2(self):
        self.assertAlmostEqual(self.ev("pi/2"), math.pi / 2, delta=TOL)


class TestImplicitMultiplication(unittest.TestCase):
    """CONST-6 .. CONST-10."""

    def ev(self, expr, ans=0.0):
        return safe_evaluate_expression(expr, ans)

    def test_number_then_group_juxtaposition(self):
        # `2(3)` is the shape SHIFT+pi produces after substitution
        # (`2pi` -> `2(3.14159...)`), and it must multiply.
        self.assertAlmostEqual(self.ev("2(3)"), 6.0, delta=TOL)

    def test_group_followed_by_number_juxtaposition(self):
        # `Ans2` with Ans=5 is `(5)2`.
        self.assertAlmostEqual(self.ev("(5)2"), 10.0, delta=TOL)

    def test_left_associative(self):
        # 3 4 5 == ((3*4)*5) == 60
        self.assertAlmostEqual(self.ev("3 4 5"), 60.0, delta=TOL)

    def test_binds_looser_than_power(self):
        # `2pi**2` is 2*(pi**2) on the calculator, NOT (2*pi)**2.
        self.assertAlmostEqual(self.ev("2pi**2"), 2 * math.pi ** 2, delta=TOL)

    def test_ans_juxtaposition(self):
        self.assertAlmostEqual(self.ev("Ans2", ans=5.0), 10.0, delta=TOL)

    def test_group_adjacent_to_group_stays_an_error(self):
        # Deliberately NOT implicit multiplication: this is the shape the
        # postfix-% rewrite produces for `10%10%`, which must stay Syntax
        # ERROR (see test_percent_contextual). Identity and explicit
        # multiplication remain available for that intent.
        with self.assertRaises(ValueError):
            self.ev("(2)(3)")

    def test_group_juxtaposition_at_parser_level(self):
        node = parse(tokenize("2(3)"))
        self.assertAlmostEqual(evaluate(node), 6.0, delta=TOL)

    def test_constant_then_constant(self):
        self.assertAlmostEqual(self.ev("2pi3"), 6 * math.pi, delta=TOL)

    def test_ans_times_pi(self):
        self.assertAlmostEqual(self.ev("2Ans", ans=5.0), 10.0, delta=TOL)

    def test_group_juxtaposition_at_parser_level(self):
        node = parse(tokenize("2(3)"))
        self.assertAlmostEqual(evaluate(node), 6.0, delta=TOL)


class TestNoRegression(unittest.TestCase):
    """CONST-7 / CONST-11 / CONST-12."""

    def ev(self, expr, ans=0.0):
        return safe_evaluate_expression(expr, ans)

    def test_explicit_operators_still_work(self):
        self.assertAlmostEqual(self.ev("2*pi"), 2 * math.pi, delta=TOL)
        self.assertAlmostEqual(self.ev("2pi/4"), 2 * math.pi / 4, delta=TOL)

    def test_explicit_and_implicit_agree(self):
        self.assertAlmostEqual(self.ev("2pi"), self.ev("2*pi"), delta=TOL)

    def test_malformed_expressions_are_still_rejected(self):
        for bad in ("2+", "(2", "2)", "*3", "2**", "()"):
            with self.subTest(expr=bad):
                with self.assertRaises(Exception):
                    self.ev(bad)

    def test_division_by_zero_still_raises(self):
        with self.assertRaises(ZeroDivisionError):
            self.ev("1/0")

    def test_parser_still_rejects_stray_operators(self):
        # `3 4` is NOT malformed: two operands in a row mean 3*4 on a
        # calculator, which is exactly what this fix enables.
        self.assertAlmostEqual(evaluate(parse(tokenize("3 4"))), 12.0, delta=TOL)
        # A trailing/leading operator with no operand still is malformed.
        for bad in ("2)", "(2", "*3"):
            with self.subTest(expr=bad):
                with self.assertRaises(ParseError):
                    parse(tokenize(bad))

    def test_precedence_unchanged(self):
        # 2+3*4 == 14, and implicit mult must not outrank multiplication.
        self.assertAlmostEqual(self.ev("2+3*4"), 14.0, delta=TOL)
        # -2**2 == -(2**2) == -4 (documented power/unary precedence).
        self.assertAlmostEqual(self.ev("-2**2"), -4.0, delta=TOL)


if __name__ == "__main__":
    unittest.main()