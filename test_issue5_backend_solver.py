"""Focused backend regressions for Issue 5 SOLVE expressions."""

import unittest

from mvp_server import CalculatorController


class TestIssue5BackendSolver(unittest.TestCase):
    def test_solve_accepts_adjacent_coefficient_variable(self):
        controller = CalculatorController()

        integer = controller.solve_equation_newton("9X+3=30", "X", 0.0)
        fraction = controller.solve_equation_newton("2X+1=0", "X", 0.0)
        alternate = controller.solve_equation_newton("2Y+4=0", "Y", 0.0)

        self.assertTrue(integer["ok"], integer)
        self.assertEqual(integer["value"], 3.0)
        self.assertTrue(fraction["ok"], fraction)
        self.assertAlmostEqual(fraction["value"], -0.5)
        self.assertTrue(alternate["ok"], alternate)
        self.assertEqual(alternate["value"], -2.0)
