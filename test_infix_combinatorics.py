"""Regression tests for the infix ``C`` combinatorics defect.

``C`` is both the ``C`` register (ALPHA + cos) and the infix ``nCr`` operator.
``safe_evaluate_expression`` substituted the word-bounded register letter
``C`` *before* ``_transform_combinatorics_infix`` ran, so every infix ``C``
form whose operator was adjacent to a non-word character lost its operator
and collapsed into ``Math ERROR``:

    (5)C(2)    -> Math ERROR      while (5)P(2) -> 20
    (5+1)C(2)  -> Math ERROR      while (5+1)P(2) -> 20
    (5)C((2))  -> Math ERROR
    5 C 2      -> Math ERROR      while 5 P 2 -> 20

``5C2`` survived only by accident: the register regex is ``\\bC\\b`` and there
is no word boundary between ``0`` and ``C``.

The fix protects the operator positions that ``_find_infix_pc`` recognises
from the ``C`` register substitution, mirroring the guard the frontend bridge
already applies in ``_transformSpecial``. Everything here goes through
``safe_evaluate_expression`` / ``CalculatorController.press_key`` - the same
evaluation boundary the rest of the backend suite uses.
"""
import unittest

from mvp_server import (
    CalculatorController,
    _find_infix_pc,
    _infix_pc_operator_indices,
    safe_evaluate_expression,
)

VARS = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0, "E": 0.0,
        "F": 0.0, "M": 0.0, "X": 0.0, "Y": 0.0}


def ev(expr, ans=0.0, variables=None, angle="Degree"):
    return safe_evaluate_expression(
        expr, ans, angle, dict(VARS if variables is None else variables))


class TestInfixCCombinatoricsOperatorSurvives(unittest.TestCase):
    """The defect itself: infix C must reach _transform_combinatorics_infix."""

    def test_parenthesised_operands(self):
        self.assertEqual(ev("(5)C(2)"), 10)
        self.assertEqual(ev("(5+1)C(2)"), 15)
        self.assertEqual(ev("(10)C(3)"), 120)

    def test_nested_parenthesised_operand(self):
        self.assertEqual(ev("(5)C((2))"), 10)

    def test_spaced_operator(self):
        self.assertEqual(ev("5 C 2"), 10)

    def test_ans_operand(self):
        self.assertEqual(ev("Ans C 2", ans=5), 10)
        self.assertEqual(ev("Ans C Ans", ans=5), 1)

    def test_p_counterparts_are_unchanged(self):
        self.assertEqual(ev("(5)P(2)"), 20)
        self.assertEqual(ev("(5+1)P(2)"), 30)
        self.assertEqual(ev("(5)P((2))"), 20)
        self.assertEqual(ev("5 P 2"), 20)

    def test_compact_and_mixed_forms_still_work(self):
        for expr in ("5C2", "(5)C2", "5C(2)", "AnsC2", "(Ans)C(2)", "10C0"):
            with self.subTest(expr=expr):
                ev(expr, ans=5)  # must not raise

    def test_invalid_still_errors(self):
        for expr in ("5C6", "(-3)C2", "0 C 5", "5 C x"):
            with self.subTest(expr=expr):
                with self.assertRaises(ValueError):
                    ev(expr, ans=5)


class TestCRegisterStillWorks(unittest.TestCase):
    """Protecting the operator must not disable the C register."""

    def setUp(self):
        self.v = dict(VARS)
        self.v["C"] = 99.0

    def test_register_reads(self):
        self.assertEqual(ev("C", variables=self.v), 99)
        self.assertEqual(ev("C+1", variables=self.v), 100)
        self.assertEqual(ev("(C)", variables=self.v), 99)
        self.assertEqual(ev("C*2", variables=self.v), 198)
        self.assertEqual(ev("2*C", variables=self.v), 198)
        self.assertEqual(ev("C-100", variables=self.v), -1)

    def test_operator_wins_over_register_value(self):
        """A stored C must not silently change nCr semantics."""
        self.assertEqual(ev("5 C 2", variables=self.v), 10)
        self.assertEqual(ev("(5)C(2)", variables=self.v), 10)
        self.assertEqual(ev("(5+1)C(2)", variables=self.v), 15)

    def test_other_registers_unaffected(self):
        v = dict(VARS)
        v["A"] = 5.0
        self.assertEqual(ev("A P 2", variables=v), 20)
        self.assertEqual(ev("(A)P(2)", variables=v), 20)
        self.assertEqual(ev("A+1", variables=v), 6)


class TestOperatorIndexHelper(unittest.TestCase):
    """_infix_pc_operator_indices must agree with _find_infix_pc exactly."""

    def test_agrees_with_finder(self):
        for s in ("5C2", "5 P 2", "(5)C(2)", "(5)P((2))", "C", "C+1",
                  "nCr(5,2)", "nPr(5,2)", "Pol(3,4)", "sin(30)", ""):
            with self.subTest(s=s):
                expected = set()
                pos = 0
                for _ in range(100):
                    found = _find_infix_pc(s, pos)
                    if found is None:
                        break
                    expected.add(found[5])
                    pos = found[5] + 1
                self.assertEqual(_infix_pc_operator_indices(s), expected)

    def test_never_marks_function_names(self):
        for s in ("nPr(5,2)", "nCr(5,2)", "Pol(3,4)", "Rec(5,60)",
                  "RanInt(1,6)", "xroot(3,27)", "sin(30)", "log(2)"):
            with self.subTest(s=s):
                self.assertEqual(_infix_pc_operator_indices(s), set())


class TestThroughCalculatorController(unittest.TestCase):
    """End-to-end through the equals key (no expression override)."""

    def _ctrl(self):
        c = CalculatorController()
        c.reset_calculator("all")
        return c

    def test_press_equals_infix_c(self):
        c = self._ctrl()
        r = c.press_key({"key": "equals", "expression": "(5)C(2)"})
        self.assertEqual(r.get("result"), "10")
        self.assertIsNone(r.get("error"))

    def test_press_equals_spaced_c(self):
        c = self._ctrl()
        r = c.press_key({"key": "equals", "expression": "5 C 2"})
        self.assertEqual(r.get("result"), "10")

    def test_press_equals_stored_c_register_unaffected(self):
        c = self._ctrl()
        c.set_variable("C", 99)
        self.assertEqual(c.press_key({"key": "equals", "expression": "C+1"})["result"], "100")
        self.assertEqual(c.press_key({"key": "equals", "expression": "5 C 2"})["result"], "10")


if __name__ == "__main__":
    unittest.main()