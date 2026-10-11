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
        self.assertTrue(self.page.evaluate("() => appState.solvePrompt.active"))
        self.press("equals")
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
        self.press("equals")
        self.page.wait_for_timeout(100)

        self.assertEqual(self.page.evaluate("() => appState.result"), "X=3")

    def test_shift_calc_opens_default_zero_guess_prompt(self):
        self.types("9")
        self.press("variable")
        self.types("+3")
        self.press("calc", alpha=True)
        self.types("30")
        self.press("calc", shift=True)

        prompt = self.page.evaluate("""() => ({
            active: !!appState.solvePrompt && appState.solvePrompt.active,
            value: appState.solvePrompt && appState.solvePrompt.value,
            text: document.querySelector('#lcdResultLine').textContent
        })""")
        self.assertEqual(prompt["active"], True)
        self.assertEqual(prompt["value"], "0")
        self.assertIn("0", prompt["text"])

    def test_solve_preserves_exact_fractional_solution(self):
        self.types("2")
        self.press("variable")
        self.types("+1")
        self.press("calc", alpha=True)
        self.types("0")
        self.press("calc", shift=True)
        self.press("equals")
        self.page.wait_for_timeout(100)

        self.assertEqual(self.page.evaluate("() => appState.result"), "X=-1/2")

    def test_solve_fraction_s_to_d_shows_decimal_assignment(self):
        self.types("2")
        self.press("variable")
        self.types("+1")
        self.press("calc", alpha=True)
        self.types("0")
        self.press("calc", shift=True)
        self.press("equals")
        self.press("s_to_d")
        self.page.wait_for_timeout(100)

        self.assertEqual(self.page.evaluate("() => appState.result"), "X=-0.5")

    def test_solve_identity_does_not_return_arbitrary_zero(self):
        self.types("2")
        self.press("variable")
        self.types("+2")
        self.press("calc", alpha=True)
        self.types("2")
        self.press("variable")
        self.types("+2")
        self.press("calc", shift=True)
        self.press("equals")
        self.page.wait_for_timeout(100)

        self.assertIsNone(self.page.evaluate("() => appState.result"))
        self.assertEqual(self.page.evaluate("() => appState.error"), "Math ERROR")

    def test_solve_supports_alpha_y_variable(self):
        self.types("2")
        self.press("variable", alpha=True)
        self.types("+4")
        self.press("calc", alpha=True)
        self.types("0")
        self.press("calc", shift=True)
        self.press("equals")
        self.page.wait_for_timeout(100)

        self.assertEqual(self.page.evaluate("() => getExpr()"), "2y+4=0")
        self.assertEqual(self.page.evaluate("() => appState.result"), "Y=-2")
