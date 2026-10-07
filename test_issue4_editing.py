"""Focused Issue 4 editing regressions driven through the real frontend."""

import unittest

from test_frontend_math_io import BrowserCase, CHROME_OK


@unittest.skipUnless(CHROME_OK, "Playwright + Chrome are required")
class TestIssue4Editing(BrowserCase):
    def test_del_on_empty_fraction_denominator_preserves_numerator(self):
        self.press("fraction")
        self.types("1")
        self.press("dpad_right")
        self.press("del")

        self.assertEqual(self.page.evaluate("() => getExpr()"), "1")

    def test_del_at_expression_beginning_is_a_noop(self):
        self.types("123")
        self.press("dpad_left")
        self.press("dpad_left")
        self.press("dpad_left")
        self.press("del")

        self.assertEqual(self.page.evaluate("() => getExpr()"), "123")
        self.assertEqual(self.cursor_state()["index"], 0)

    def test_ac_clears_insert_mode_with_structured_editing_state(self):
        self.press("fraction")
        self.types("1")
        self.press("dpad_right")
        self.types("2")
        self.page.evaluate("""() => {
            appState.insertMode = true;
            appState.result = 42;
            appState.resultDisplayed = true;
            appState.error = 'Math ERROR';
            renderLCD();
        }""")

        self.press("ac")

        state = self.page.evaluate("""() => ({
            expr: getExpr(), result: appState.result,
            resultDisplayed: appState.resultDisplayed, error: appState.error,
            insertMode: appState.insertMode, cursorIndex: cursor.index,
            cursorIsRoot: cursor.slot === rootSlot
        })""")
        self.assertEqual(state, {
            "expr": "", "result": None, "resultDisplayed": False,
            "error": None, "insertMode": False, "cursorIndex": 0,
            "cursorIsRoot": True
        })
