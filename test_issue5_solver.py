"""Focused Issue 5 SOLVE regressions driven through the real frontend."""

import unittest

from test_frontend_math_io import BrowserCase, CHROME_OK


@unittest.skipUnless(CHROME_OK, "Playwright + Chrome are required")
class TestIssue5Solve(BrowserCase):
    def test_shift_calc_solves_linear_equation_from_physical_keys(self):
        self.types("9")
        self.press("variable")
        self.types("+3")
        self.press("calc", alpha=True)
        self.types("30")
        self.assertEqual(self.page.evaluate("() => getExpr()"), "9X+3=30")

        self.press("calc", shift=True)
        self.page.wait_for_timeout(100)

        self.assertIsNone(self.page.evaluate("() => appState.error"))
        self.assertTrue(self.page.evaluate("() => appState.resultDisplayed"))
        self.assertEqual(self.page.evaluate("() => appState.variables.X"), 3)

    def test_solve_displays_variable_assignment(self):
        self.types("9")
        self.press("variable")
        self.types("+3")
        self.press("calc", alpha=True)
        self.types("30")
        self.press("calc", shift=True)
        self.page.wait_for_timeout(100)

        self.assertEqual(self.page.evaluate("() => appState.result"), "X=3")
