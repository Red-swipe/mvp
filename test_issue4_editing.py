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
